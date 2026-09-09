# Quazi for Zed

This Zed extension registers `.qz`, pins `tree-sitter-quazi` to
`c3d5c29393c9bcfce498f3c2f7b3a6f2c8026896`, and starts `qz lsp` from `PATH`.
Develop locally with Zed's **Install Dev Extension** command. It does not bundle
the compiler; install `qz` separately.

From this workspace, verify the pinned grammar revision and highlight query:

```bash
bash tests/check-canonical-assets.sh
```
