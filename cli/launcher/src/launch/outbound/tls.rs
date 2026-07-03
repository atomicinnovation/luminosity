//! Installs the rustls crypto provider the launcher's TLS stack requires.
//!
//! reqwest/rustls 0.23 default to `aws-lc-rs` (C + per-arch assembly, hostile to
//! the four-triple cross-build), so the launcher pins the pure-Rust `ring`
//! provider (the `-no-provider` reqwest feature + a direct rustls `ring` dep)
//! and installs it as the process default before any request. The install is
//! fallible and is mapped into [`kernel::Error`], never `unwrap`ped.

/// Install the `ring` crypto provider as the process default.
///
/// Idempotent: an already-installed provider (the `Err` case) is benign — some
/// provider is present, which is all TLS needs — so it is treated as success.
///
/// # Errors
///
/// Never, currently: the only failure `install_default` reports is "already
/// installed", which is fine. The `Result` is the seam where a genuinely
/// fallible provider setup would surface as a [`kernel::Error`].
pub fn install_crypto_provider() -> Result<(), kernel::Error> {
    // Ignore the "already installed" Err: it means a provider is present, which
    // is the post-condition we want. Not `unwrap`ped (restriction lints).
    let _ = rustls::crypto::ring::default_provider().install_default();
    Ok(())
}
