# Quazi for Zed

This Zed extension registers `.qz`, pins `tree-sitter-quazi` to
`1bc33fcdd937635326355ce5dc1767ab17701194`, and starts `qz lsp` from `PATH`.
Develop locally with Zed's **Install Dev Extension** command. It does not bundle
the compiler; install `qz` separately.

From this workspace, verify the pinned grammar revision and highlight query:

```bash
bash tests/check-canonical-assets.sh
```
