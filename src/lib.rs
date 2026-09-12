use zed_extension_api as zed;

struct QuaziExtension;

impl zed::Extension for QuaziExtension {
    fn new() -> Self {
        Self
    }

    fn language_server_command(
        &mut self,
        _language_server_id: &zed::LanguageServerId,
        worktree: &zed::Worktree,
    ) -> zed::Result<zed::Command> {
        let path = worktree
            .which("qz")
            .ok_or_else(|| "qz not found in PATH".to_string())?;

        Ok(zed::Command {
            command: path,
            args: vec!["lsp".into()],
            env: Default::default(),
        })
    }
}

zed::register_extension!(QuaziExtension);
