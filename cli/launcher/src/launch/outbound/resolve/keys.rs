//! The trusted release public key(s) and in-process minisign verification.
//!
//! The minisign signature is the security boundary (sha256 is only a corruption
//! check). Verification supports a small set of trusted keys — verify-any-of —
//! so key rotation has an overlap window rather than a hard cutover.

use minisign_verify::{PublicKey, Signature};

use crate::launch::core::ResolutionError;

/// The committed release public key the launcher embeds. Kept byte-identical to
/// the plugin-package copy by `version:check` (key coherence).
pub const EMBEDDED_RELEASE_KEY: &str =
    include_str!("../../../../keys/release.pub");

/// A set of trusted public keys; a signature is accepted if ANY key verifies it.
pub struct TrustedKeys {
    keys: Vec<PublicKey>,
}

impl TrustedKeys {
    /// Parse minisign `.pub` file contents (comment line + base64 line each).
    ///
    /// # Errors
    ///
    /// [`ResolutionError::Cache`] (used as a generic startup-config error) if a
    /// key cannot be parsed — a misconfigured trust root must fail closed.
    pub fn from_public_key_files(
        contents: &[&str],
    ) -> Result<Self, ResolutionError> {
        let mut keys = Vec::with_capacity(contents.len());
        for content in contents {
            let base64 = content
                .lines()
                .find(|line| {
                    !line.trim_start().starts_with("untrusted comment")
                })
                .map(str::trim)
                .filter(|line| !line.is_empty())
                .ok_or_else(|| ResolutionError::CacheRootUnavailable {
                    detail: "trusted public key has no key line".to_owned(),
                })?;
            let key = PublicKey::from_base64(base64).map_err(|error| {
                ResolutionError::CacheRootUnavailable {
                    detail: format!("invalid trusted public key: {error}"),
                }
            })?;
            keys.push(key);
        }
        Ok(Self { keys })
    }

    /// The launcher's production trust root: just the embedded release key.
    ///
    /// # Errors
    ///
    /// If the embedded key cannot be parsed (a build-time misconfiguration).
    pub fn embedded() -> Result<Self, ResolutionError> {
        Self::from_public_key_files(&[EMBEDDED_RELEASE_KEY])
    }

    /// Whether `signature` (a `.minisig` file's contents) verifies `data` under
    /// any trusted key. Any parse/verify failure is a non-match, never a panic.
    #[must_use]
    pub fn verifies(&self, data: &[u8], signature: &str) -> bool {
        let Ok(parsed) = Signature::decode(signature) else {
            return false;
        };
        self.keys
            .iter()
            .any(|key| key.verify(data, &parsed, false).is_ok())
    }
}
