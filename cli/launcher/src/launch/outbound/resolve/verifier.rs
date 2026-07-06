//! Verification: sha256 (corruption check) + minisign (the security boundary,
//! proving "signed by our key", not merely "served over TLS").

use std::fmt::Write as _;

use sha2::{Digest as _, Sha256};

use crate::launch::core::ResolutionError;

use super::keys::TrustedKeys;

#[must_use]
pub fn sha256_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    let mut hex = String::with_capacity(digest.len() * 2);
    for byte in digest {
        let _ = write!(hex, "{byte:02x}");
    }
    hex
}

/// # Errors
///
/// [`ResolutionError::ChecksumMismatch`] if `bytes` do not match
/// `expected_sha256`, or [`ResolutionError::SignatureMismatch`] if no trusted
/// key verifies the signature.
pub fn verify_binary(
    asset: &str,
    bytes: &[u8],
    expected_sha256: &str,
    signature: &str,
    keys: &TrustedKeys,
) -> Result<(), ResolutionError> {
    let actual = sha256_hex(bytes);
    if actual != expected_sha256 {
        return Err(ResolutionError::ChecksumMismatch {
            asset: asset.to_owned(),
            expected: expected_sha256.to_owned(),
            actual,
        });
    }
    if !keys.verifies(bytes, signature) {
        return Err(ResolutionError::SignatureMismatch {
            asset: asset.to_owned(),
        });
    }
    Ok(())
}

/// # Errors
///
/// [`ResolutionError::ManifestSignature`] if no trusted key verifies the
/// manifest signature.
pub fn verify_manifest(
    manifest_bytes: &[u8],
    manifest_signature: &str,
    keys: &TrustedKeys,
) -> Result<(), ResolutionError> {
    if keys.verifies(manifest_bytes, manifest_signature) {
        Ok(())
    } else {
        Err(ResolutionError::ManifestSignature)
    }
}

#[cfg(test)]
mod tests {
    use super::sha256_hex;

    #[test]
    fn sha256_hex_matches_a_known_vector() {
        // echo -n "" | sha256sum
        assert_eq!(
            sha256_hex(b""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
    }
}
