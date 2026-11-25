# Quazi for Zed

This Zed extension registers `.qz`, pins `tree-sitter-quazi` to the `rev` in
`extension.toml` (currently `cb8eee528b00decba801f5e7a6e74a509c57700f`), and
starts `qz lsp` from `PATH`.
Develop locally with Zed's **Install Dev Extension** command. It does not bundle
the compiler; install `qz` separately.

From this workspace, verify the pinned grammar revision and highlight query:

```bash
bash tests/check-canonical-assets.sh
```

Zed compiles the extension to WebAssembly when it installs it. The same build
works without Zed (with the `wasm32-wasip2` Rust target installed):

```bash
cargo build --release --target wasm32-wasip2
```

`tests/runtime-smoke.py` validates the extension inside a running Zed without
a GPU: Zed runs on Xvfb with Mesa's software Vulkan driver (lavapipe) and an
isolated home directory. The test installs a copy of this extension through
the command palette (**zed: install dev extension**, with
`use_system_path_prompts` off), so Zed itself compiles the extension and the
grammar to WebAssembly; then it opens a `.qz` file and drives **editor: hover**
and **editor: go to definition** with `xdotool`. `qz` runs behind a logging
proxy, and the test requires Zed to start `qz lsp`, open the document, and get
answers to both requests. Until the pinned grammar revision is published, the
copy fetches it from the local `../tree-sitter` checkout (`file://`). Zed
downloads the WASI SDK on the first build (network access), and the Rust
toolchain needs the `wasm32-wasip2` target. Verified with Zed 1.28.1 from
nixpkgs:

```bash
nixpkg() { nix build "nixpkgs#$1" --no-link --print-out-paths; }
python3 tests/runtime-smoke.py \
  --zed "$(nixpkg zed-editor)/bin/zeditor" --qz /path/to/qz \
  --xvfb "$(nixpkg xorg.xorgserver)/bin/Xvfb" \
  --xdotool "$(nixpkg xdotool)/bin/xdotool" \
  --vulkan-icd "$(nixpkg mesa)/share/vulkan/icd.d/lvp_icd.x86_64.json" \
  --library-path "$(nixpkg ncurses)/lib"
```

`--library-path` is needed where the downloaded WASI SDK `clang` cannot find
`libtinfo.so.6` (for example NixOS with nix-ld). The test prints
`PASS zed runtime: ...` and exits non-zero on failure; `--screenshot FILE`
saves the screen when it fails (needs ImageMagick `import`).
