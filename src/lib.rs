use zed_extension_api as zed;

struct QuaziExtension;

impl zed::Extension for QuaziExtension {
    fn new() -> Self {
        Self
    }

    fn language_server_command(
        &mut self,
        _language_server_id: &zed::LanguageServerId,
        _worktree: &zed::Worktree,
    ) -> zed::Result<zed::Command> {
        Ok(zed::Command {
            command: "qz".into(),
            args: vec!["lsp".into()],
            env: Default::default(),
        })
    }
}

zed::register_extension!(QuaziExtension);
