#!/usr/bin/env python3
"""Reproducible Zed runtime validation of the Quazi extension.

Zed runs on a virtual X server (Xvfb) with Mesa's software Vulkan driver
(lavapipe), so no GPU is needed. The test uses an isolated home directory,
installs a copy of this extension as a dev extension through the command
palette (Zed compiles the extension and the grammar to WebAssembly itself),
opens a `.qz` file, and drives hover (`editor: hover`) and go to definition
(`editor: go to definition`) with keystrokes. `qz` is reached through a
logging proxy on PATH; the test requires Zed to send each request for the
open document and the server to answer it with a result.

The pinned grammar revision may not be published yet, so the copy points the
grammar `repository` at the local tree-sitter checkout (`file://`) at the
same revision. Zed downloads the WASI SDK on the first dev-extension build,
which needs network access.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parent.parent

SOURCE = """fn helper(count: i32) i32 { ret count; }

fn main() i32 {
    const total: i32 = helper(2);
    ret total;
}
"""

PROXY = r'''
import json, subprocess, sys, threading
log = open(sys.argv[1], "a", buffering=1)
server = subprocess.Popen(sys.argv[2:], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

def pump(source, sink, direction):
    while True:
        headers = {}
        while True:
            line = source.readline()
            if not line:
                sink.close()
                return
            if line in (b"\r\n", b"\n"):
                break
            name, _, value = line.decode().partition(":")
            headers[name.strip().lower()] = value.strip()
        body = source.read(int(headers["content-length"]))
        log.write(json.dumps({"direction": direction, "message": json.loads(body)}) + "\n")
        sink.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
        sink.flush()

threading.Thread(target=pump, args=(server.stdout, sys.stdout.buffer, "server"), daemon=True).start()
pump(sys.stdin.buffer, server.stdin, "client")
server.wait()
'''


def messages(log):
    if not log.exists():
        return []
    entries = []
    for line in log.read_text().splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass  # a line still being written
    return entries


def answered(log, method):
    """Result of the last answered `method` request, or None."""
    entries = messages(log)
    ids = {entry["message"]["id"] for entry in entries
           if entry["direction"] == "client" and entry["message"].get("method") == method}
    results = [entry["message"].get("result") for entry in entries
               if entry["direction"] == "server" and entry["message"].get("id") in ids
               and "method" not in entry["message"]]
    return results[-1] if results else None


def opened(log, uri_suffix):
    return any(entry["direction"] == "client"
               and entry["message"].get("method") == "textDocument/didOpen"
               and entry["message"]["params"]["textDocument"]["uri"].endswith(uri_suffix)
               for entry in messages(log))


def wait_for(predicate, seconds, description, on_timeout):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.5)
    on_timeout()
    raise SystemExit(f"FAIL zed runtime: timed out waiting for {description}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--zed", required=True, help="the Zed executable (zeditor or zed)")
    parser.add_argument("--qz", required=True, help="the qz executable")
    parser.add_argument("--xvfb", default="Xvfb")
    parser.add_argument("--xdotool", default="xdotool")
    parser.add_argument("--vulkan-icd", required=True,
                        help="Mesa lavapipe ICD file, for example .../share/vulkan/icd.d/lvp_icd.x86_64.json")
    parser.add_argument("--tree-sitter", default=str(REPOSITORY.parent / "tree-sitter"))
    parser.add_argument("--screenshot", help="save a screenshot here on failure (needs ImageMagick `import`)")
    parser.add_argument("--display", default=":97")
    parser.add_argument("--library-path", action="append", default=[],
                        help="extra shared-library directory for the WASI SDK clang that Zed "
                             "downloads (it needs libtinfo.so.6; on NixOS it runs through nix-ld)")
    args = parser.parse_args()

    work = Path(tempfile.mkdtemp(prefix="quazi-zed-"))
    processes = []
    try:
        home = work / "home"
        extension = work / "zed-quazi"
        project = work / "project"
        bin_dir = work / "bin"
        log = work / "lsp.jsonl"
        for directory in (home / ".config/zed", project, bin_dir):
            directory.mkdir(parents=True)

        shutil.copytree(REPOSITORY, extension, ignore=shutil.ignore_patterns("target", ".git"))
        manifest = (extension / "extension.toml").read_text()
        grammar = Path(args.tree_sitter).resolve()
        manifest = manifest.replace('repository = "https://github.com/quazilang/tree-sitter"',
                                    f'repository = "file://{grammar}"')
        (extension / "extension.toml").write_text(manifest)

        (bin_dir / "qz-proxy.py").write_text(PROXY)
        wrapper = bin_dir / "qz"
        wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{bin_dir / "qz-proxy.py"}" "{log}" '
                           f'"{Path(args.qz).resolve()}" "$@"\n')
        wrapper.chmod(0o755)

        (project / "quazi.toml").write_text('[package]\nname = "zed-smoke"\nversion = "0.1.0"\n')
        (project / "main.qz").write_text(SOURCE)
        (home / ".config/zed/settings.json").write_text(json.dumps({
            "session": {"trust_all_worktrees": True},
            "use_system_path_prompts": False,
            "telemetry": {"diagnostics": False, "metrics": False},
            "auto_update": False,
            "restore_on_startup": "none",
        }))

        env = {key: value for key, value in os.environ.items()
               if key not in ("WAYLAND_DISPLAY", "QUAZI_LSP_COMMAND")}
        # Zed compiles the extension with the user's Rust toolchain (it needs
        # the wasm32-wasip2 target); keep rustup's homes outside the isolated one.
        real_home = Path.home()
        env.setdefault("RUSTUP_HOME", str(real_home / ".rustup"))
        env.setdefault("CARGO_HOME", str(real_home / ".cargo"))
        env.update({
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_DATA_HOME": str(home / ".local/share"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_STATE_HOME": str(home / ".local/state"),
            "PATH": f"{bin_dir}{os.pathsep}{env.get('PATH', '')}",
            "DISPLAY": args.display,
            "VK_ICD_FILENAMES": args.vulkan_icd,
            "ZED_ALLOW_EMULATED_GPU": "1",
        })
        for variable in ("LD_LIBRARY_PATH", "NIX_LD_LIBRARY_PATH"):
            if args.library_path and (variable == "LD_LIBRARY_PATH" or variable in env):
                env[variable] = os.pathsep.join(args.library_path + [env.get(variable, "")]).rstrip(os.pathsep)
        zed_log = home / ".local/share/zed/logs/Zed.log"

        def keys(*sequence):
            for item in sequence:
                subprocess.run([args.xdotool, "key", "--clearmodifiers", item], env=env, check=True)
                time.sleep(0.4)

        def type_text(text):
            subprocess.run([args.xdotool, "type", "--delay", "40", text], env=env, check=True)
            time.sleep(0.4)

        def command(name):
            keys("ctrl+shift+p")
            time.sleep(1)
            type_text(name)
            time.sleep(1)
            keys("Return")

        def dump():
            if args.screenshot and shutil.which("import"):
                subprocess.run(["import", "-window", "root", args.screenshot], env=env)
            if zed_log.exists():
                print("\n".join(zed_log.read_text().splitlines()[-40:]), file=sys.stderr)

        processes.append(subprocess.Popen([args.xvfb, args.display, "-screen", "0", "1280x800x24"],
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        time.sleep(1)
        processes.append(subprocess.Popen([args.zed, "--foreground", str(project)], env=env,
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))

        wait_for(lambda: zed_log.exists() and "Found" in zed_log.read_text() and "GPU adapter" in zed_log.read_text(),
                 60, "the Zed window", dump)
        time.sleep(5)

        command("zed: install dev extension")
        time.sleep(2)
        keys("ctrl+a")
        type_text(str(extension) + "/")
        keys("Return")
        def built():
            text = zed_log.read_text()
            if "Failed to install dev extension" in text:
                dump()
                raise SystemExit("FAIL zed runtime: the dev extension did not build")
            start = text.find("compiling grammar quazi")
            return start >= 0 and "extensions updated" in text[start:]

        wait_for(built, 600, "the dev extension build", dump)
        time.sleep(5)

        keys("ctrl+p")
        time.sleep(1)
        type_text("main.qz")
        time.sleep(1)
        keys("Return")
        wait_for(lambda: opened(log, "/main.qz"), 120, "didOpen of main.qz through qz lsp", dump)
        wait_for(lambda: any(entry["direction"] == "server"
                             and entry["message"].get("method") == "textDocument/publishDiagnostics"
                             for entry in messages(log)),
                 60, "analysis of main.qz", dump)

        # Line 4 (`const total: i32 = helper(2);`): put the cursor on `helper`.
        command("go to line")
        time.sleep(1)
        type_text("4:24")
        keys("Return")
        time.sleep(1)
        command("editor: hover")
        hover = wait_for(lambda: answered(log, "textDocument/hover"), 30, "a hover answer", dump)
        contents = hover.get("contents") if isinstance(hover, dict) else None
        if not contents or "i32" not in json.dumps(contents):
            dump()
            raise SystemExit(f"FAIL zed runtime: hover did not describe the call: {hover}")

        command("editor: go to definition")
        definition = wait_for(lambda: answered(log, "textDocument/definition"), 30,
                              "a definition answer", dump)
        location = definition[0] if isinstance(definition, list) else definition
        target = location.get("targetRange") or location.get("range")
        if target["start"]["line"] != 0:
            dump()
            raise SystemExit(f"FAIL zed runtime: definition of helper is not on line 1: {definition}")

        print("PASS zed runtime: dev extension built and installed, qz lsp hover and definition answered")
    finally:
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
