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

Running the extension inside Zed (dev-extension install, grammar compilation
to WebAssembly, and LSP requests) has not been verified here: Zed needs a GPU
display.
