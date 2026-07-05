//! The release manifest — the launcher's signed read contract. Deserialised
//! leniently (unknown fields ignored) so it can gain additive fields, but a
//! `schema_version` higher than supported fails closed.

use std::collections::BTreeMap;

use serde::Deserialize;

use crate::launch::core::ResolutionError;

/// The manifest schema the launcher understands; kept coherent with
/// `tasks/sign.py`'s `MANIFEST_SCHEMA_VERSION`.
pub const SUPPORTED_SCHEMA_VERSION: u64 = 1;

#[derive(Debug, Deserialize)]
pub struct Manifest {
    pub schema_version: u64,
    pub version: String,
    #[serde(default)]
    pub binaries: BTreeMap<String, BinaryEntry>,
}

#[derive(Debug, Deserialize)]
pub struct BinaryEntry {
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub platforms: BTreeMap<String, PlatformEntry>,
}

#[derive(Debug, Deserialize)]
pub struct PlatformEntry {
    pub sha256: String,
    pub signature: String,
}

impl Manifest {
    /// Parse manifest JSON, then assert the schema is supported and the version
    /// matches the launcher's own (anti-rollback). Call only AFTER verifying the
    /// manifest signature.
    ///
    /// # Errors
    ///
    /// [`ResolutionError::UnsupportedSchema`] or
    /// [`ResolutionError::ManifestVersionMismatch`].
    pub fn parse_and_validate(
        bytes: &[u8],
        expected_version: &str,
    ) -> Result<Self, ResolutionError> {
        let manifest: Self =
            serde_json::from_slice(bytes).map_err(|error| {
                ResolutionError::Cache {
                    path: "manifest.json".into(),
                    detail: format!("manifest is not valid JSON: {error}"),
                }
            })?;
        if manifest.schema_version > SUPPORTED_SCHEMA_VERSION {
            return Err(ResolutionError::UnsupportedSchema {
                found: manifest.schema_version,
                supported: SUPPORTED_SCHEMA_VERSION,
            });
        }
        if manifest.version != expected_version {
            return Err(ResolutionError::ManifestVersionMismatch {
                expected: expected_version.to_owned(),
                actual: manifest.version,
            });
        }
        Ok(manifest)
    }

    #[must_use]
    pub fn platform_entry(
        &self,
        binary: &str,
        platform: &str,
    ) -> Option<&PlatformEntry> {
        self.binaries.get(binary)?.platforms.get(platform)
    }
}

#[cfg(test)]
mod tests {
    use std::error::Error;

    use super::{Manifest, SUPPORTED_SCHEMA_VERSION};

    const SHARED_FIXTURE: &str =
        include_str!("../../../../tests/fixtures/manifest.example.json");

    #[test]
    fn parses_the_shared_fixture_the_python_writer_emits(
    ) -> Result<(), Box<dyn Error>> {
        let manifest = Manifest::parse_and_validate(
            SHARED_FIXTURE.as_bytes(),
            "0.1.0-pre.1",
        )?;
        let launcher = manifest
            .platform_entry("luminosity", "darwin-arm64")
            .ok_or("missing luminosity/darwin-arm64")?;
        assert_eq!(launcher.sha256.len(), 64);
        assert!(!launcher.signature.is_empty());
        let foo = manifest.binaries.get("foo").ok_or("missing foo")?;
        assert_eq!(foo.description, "Bar tool");
        Ok(())
    }

    #[test]
    fn rejects_an_unsupported_higher_schema() {
        let json = format!(
            "{{\"schema_version\": {}, \"version\": \"1.0.0\", \
             \"binaries\": {{}}}}",
            SUPPORTED_SCHEMA_VERSION + 1
        );
        assert!(Manifest::parse_and_validate(json.as_bytes(), "1.0.0").is_err());
    }

    #[test]
    fn rejects_a_version_mismatch() {
        let json = "{\"schema_version\": 1, \"version\": \"9.9.9\", \
                    \"binaries\": {}}";
        assert!(Manifest::parse_and_validate(json.as_bytes(), "1.0.0").is_err());
    }

    #[test]
    fn ignores_unknown_additive_fields() -> Result<(), Box<dyn Error>> {
        let json = "{\"schema_version\": 1, \"version\": \"1.0.0\", \
                    \"future_field\": 42, \"binaries\": {}}";
        Manifest::parse_and_validate(json.as_bytes(), "1.0.0")?;
        Ok(())
    }
}
