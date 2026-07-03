//! The real fetch → verify → cache → resolve adapter and its collaborators.
//!
//! Composes a [`Fetcher`] (transport), a [`verifier`] (manifest signature +
//! version binding, then per-binary sha256 + minisign), a [`cache`] store
//! (atomic write + prefix-scan lookup keyed by name+version+checksum), and a
//! resolved cache root. Each collaborator is independently unit-tested; this
//! module orchestrates them behind the `ResolveBinary` port.

pub mod cache;
pub mod cache_root;
pub mod fetcher;
pub mod keys;
pub mod manifest;
pub mod verifier;

use std::path::PathBuf;

use crate::launch::core::{ExternalCommand, ResolutionError, ResolveBinary};

use self::cache::CachedBinary;
use self::fetcher::{FetchError, Fetcher};
use self::keys::TrustedKeys;
use self::manifest::Manifest;

/// The host platform alias this launcher was built for — the single Rust source
/// of the triple→alias map, asserted equal to `tasks/shared/targets.py` by a
/// cross-language coherence test.
#[cfg(all(target_arch = "aarch64", target_os = "macos"))]
pub const HOST_PLATFORM: &str = "darwin-arm64";
#[cfg(all(target_arch = "x86_64", target_os = "macos"))]
pub const HOST_PLATFORM: &str = "darwin-x64";
#[cfg(all(target_arch = "aarch64", target_os = "linux"))]
pub const HOST_PLATFORM: &str = "linux-arm64";
#[cfg(all(target_arch = "x86_64", target_os = "linux"))]
pub const HOST_PLATFORM: &str = "linux-x64";

const DEFAULT_RETAINED_VERSIONS: usize = 3;

/// Configuration for the resolver — injected so tests point it at a mock server
/// and a temp cache root.
pub struct ResolverConfig {
    /// The launcher's own version; the manifest must match it (anti-rollback).
    pub expected_version: String,
    /// The host platform alias (`HOST_PLATFORM` in production).
    pub platform: String,
    /// The release-download base URL (no trailing slash), pinned to the
    /// plugin's own `v{version}` tag in production.
    pub base_url: String,
    /// Where cached binaries live (resolved via `cache_root` in production).
    pub cache_root: PathBuf,
    /// Bound on retained versions per binary (host-un-GC'd XDG growth cap).
    pub retained_versions: usize,
}

impl ResolverConfig {
    /// Build the production config from the base URL and resolved cache root.
    #[must_use]
    pub fn production(base_url: String, cache_root: PathBuf) -> Self {
        Self {
            expected_version: env!("CARGO_PKG_VERSION").to_owned(),
            platform: HOST_PLATFORM.to_owned(),
            base_url,
            cache_root,
            retained_versions: DEFAULT_RETAINED_VERSIONS,
        }
    }
}

/// The real `ResolveBinary` adapter: cache-hit re-verify, else fetch → verify →
/// cache.
pub struct FetchVerifyCacheResolver {
    config: ResolverConfig,
    keys: TrustedKeys,
    fetcher: Fetcher,
}

impl FetchVerifyCacheResolver {
    /// # Errors
    ///
    /// If the HTTP client cannot be built.
    pub fn new(
        config: ResolverConfig,
        keys: TrustedKeys,
    ) -> Result<Self, ResolutionError> {
        let fetcher = Fetcher::new().map_err(|detail| {
            ResolutionError::CacheRootUnavailable { detail }
        })?;
        Ok(Self {
            config,
            keys,
            fetcher,
        })
    }

    /// Construct with a caller-supplied fetcher (tests inject a tiny backoff).
    #[must_use]
    pub const fn with_fetcher(
        config: ResolverConfig,
        keys: TrustedKeys,
        fetcher: Fetcher,
    ) -> Self {
        Self {
            config,
            keys,
            fetcher,
        }
    }

    fn reverify(&self, cached: &CachedBinary) -> Result<(), ResolutionError> {
        let bytes = std::fs::read(&cached.path).map_err(|error| {
            ResolutionError::Cache {
                path: cached.path.clone(),
                detail: error.to_string(),
            }
        })?;
        let signature = std::fs::read_to_string(&cached.signature_path)
            .map_err(|error| ResolutionError::Cache {
                path: cached.signature_path.clone(),
                detail: error.to_string(),
            })?;
        verifier::verify_binary(
            &file_name(&cached.path),
            &bytes,
            &cached.sha256,
            &signature,
            &self.keys,
        )
    }

    /// Fetch, signature-verify, and version/schema-validate the release
    /// manifest — the shared front half of resolution and help synthesis.
    ///
    /// # Errors
    ///
    /// A [`ResolutionError`] on fetch/signature/version/schema failure.
    pub fn load_manifest(&self) -> Result<Manifest, ResolutionError> {
        let base = &self.config.base_url;
        let manifest_url = format!("{base}/manifest.json");
        let manifest_bytes =
            self.fetcher.get(&manifest_url).map_err(|error| {
                fetch_error(&error, &self.config.platform, &manifest_url, true)
            })?;
        let signature_url = format!("{base}/manifest.minisig");
        let signature_bytes =
            self.fetcher.get(&signature_url).map_err(|error| {
                fetch_error(&error, &self.config.platform, &signature_url, true)
            })?;
        let signature = String::from_utf8_lossy(&signature_bytes);
        verifier::verify_manifest(&manifest_bytes, &signature, &self.keys)?;
        Manifest::parse_and_validate(
            &manifest_bytes,
            &self.config.expected_version,
        )
    }

    fn fetch_verify_store(
        &self,
        name: &str,
    ) -> Result<PathBuf, ResolutionError> {
        let base = &self.config.base_url;
        let manifest = self.load_manifest()?;
        let asset_name = format!("{name}-{}", self.config.platform);
        let asset_url = format!("{base}/{asset_name}");
        let entry = manifest
            .platform_entry(name, &self.config.platform)
            .ok_or_else(|| ResolutionError::AssetNotFound {
                target: asset_name.clone(),
                url: asset_url.clone(),
            })?;

        let bytes = self.fetcher.get(&asset_url).map_err(|error| {
            fetch_error(&error, &asset_name, &asset_url, false)
        })?;
        verifier::verify_binary(
            &asset_name,
            &bytes,
            &entry.sha256,
            &entry.signature,
            &self.keys,
        )?;

        let cached = cache::store(
            &self.config.cache_root,
            name,
            &self.config.expected_version,
            &entry.sha256,
            &bytes,
            &entry.signature,
        )?;
        cache::enforce_retention_cap(
            &self.config.cache_root,
            name,
            self.config.retained_versions,
        );
        Ok(cached.path)
    }
}

impl ResolveBinary for FetchVerifyCacheResolver {
    fn resolve(
        &self,
        command: &ExternalCommand,
    ) -> Result<PathBuf, ResolutionError> {
        let name = command.name.to_str().ok_or_else(|| {
            ResolutionError::Unresolved {
                name: command.name.clone(),
            }
        })?;

        if let Some(cached) = cache::find(
            &self.config.cache_root,
            name,
            &self.config.expected_version,
        ) {
            // Re-verify before every exec, including cache hits: the cache dir
            // is user-writable, so a poisoned entry (binary + matching sha) must
            // still be caught by the signature. On failure, self-heal.
            match self.reverify(&cached) {
                Ok(()) => return Ok(cached.path),
                Err(_) => cache::evict(&cached),
            }
        }
        self.fetch_verify_store(name)
    }
}

fn file_name(path: &std::path::Path) -> String {
    path.file_name()
        .map(|name| name.to_string_lossy().into_owned())
        .unwrap_or_default()
}

fn fetch_error(
    error: &FetchError,
    target: &str,
    url: &str,
    is_manifest: bool,
) -> ResolutionError {
    match error {
        FetchError::NotFound if is_manifest => {
            ResolutionError::ReleaseUnavailable {
                target: target.to_owned(),
                url: url.to_owned(),
            }
        }
        FetchError::NotFound => ResolutionError::AssetNotFound {
            target: target.to_owned(),
            url: url.to_owned(),
        },
        FetchError::Unreachable(_) => ResolutionError::Fetch {
            target: target.to_owned(),
            url: url.to_owned(),
        },
    }
}
