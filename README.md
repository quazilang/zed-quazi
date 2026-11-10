# Quazi for Zed

This Zed extension registers `.qz`, pins `tree-sitter-quazi` to
`22c684a0d89d5be381d07b6460528db9bee4fcad`, and starts `qz lsp` from `PATH`.
Develop locally with Zed's **Install Dev Extension** command. It does not bundle
the compiler; install `qz` separately.

From this workspace, verify the pinned grammar revision and highlight query:

```bash
bash tests/check-canonical-assets.sh
```
