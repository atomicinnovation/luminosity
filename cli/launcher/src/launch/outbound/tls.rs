//! Installs the pure-Rust `ring` crypto provider rustls needs, chosen over the
//! default `aws-lc-rs` (C + per-arch assembly, hostile to the cross-build).

/// Install the `ring` crypto provider as the process default (idempotent).
///
/// # Errors
///
/// Never currently — an already-installed provider is treated as success. The
/// `Result` is the seam for a genuinely fallible setup.
pub fn install_crypto_provider() -> Result<(), kernel::Error> {
    let _ = rustls::crypto::ring::default_provider().install_default();
    Ok(())
}
