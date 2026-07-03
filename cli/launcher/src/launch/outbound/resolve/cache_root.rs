//! Resolves the runtime cache directory.
//!
//! Prefers the plugin root (`${CLAUDE_PLUGIN_ROOT}/bin`, so Claude Code reclaims
//! it on upgrade) when writable and exec-capable, else an XDG fallback, else a
//! named error. `LUMINOSITY_CACHE_DIR` overrides. Read-only installs and
//! `noexec` mounts are probed, not inferred.

use std::path::{Path, PathBuf};
use std::process::Command;

use crate::launch::core::ResolutionError;

/// The environment inputs the resolution needs — injected so tests supply temp
/// dirs instead of reading the real process environment.
pub struct CacheRootConfig {
    pub cache_dir_override: Option<PathBuf>,
    pub plugin_root: Option<PathBuf>,
    pub xdg_cache_home: Option<PathBuf>,
    pub home: Option<PathBuf>,
}

impl CacheRootConfig {
    /// Read the config from the process environment.
    #[must_use]
    pub fn from_env() -> Self {
        Self {
            cache_dir_override: std::env::var_os("LUMINOSITY_CACHE_DIR")
                .filter(|value| !value.is_empty())
                .map(PathBuf::from),
            plugin_root: std::env::var_os("CLAUDE_PLUGIN_ROOT")
                .filter(|value| !value.is_empty())
                .map(PathBuf::from),
            xdg_cache_home: std::env::var_os("XDG_CACHE_HOME")
                .filter(|value| !value.is_empty())
                .map(PathBuf::from),
            home: std::env::var_os("HOME")
                .filter(|value| !value.is_empty())
                .map(PathBuf::from),
        }
    }

    fn xdg_fallback(&self) -> Option<PathBuf> {
        if let Some(base) = &self.xdg_cache_home {
            return Some(base.join("luminosity"));
        }
        let home = self.home.as_ref()?;
        // Darwin conventionally caches under ~/Library/Caches.
        if cfg!(target_os = "macos") {
            Some(home.join("Library/Caches/luminosity"))
        } else {
            Some(home.join(".cache/luminosity"))
        }
    }
}

/// Resolve a writable, exec-capable cache directory (creating it if needed).
///
/// # Errors
///
/// [`ResolutionError::CacheRootUnavailable`] when no candidate is usable — an
/// unset `CLAUDE_PLUGIN_ROOT` with no override, or every candidate failing the
/// write+exec probe.
pub fn resolve(config: &CacheRootConfig) -> Result<PathBuf, ResolutionError> {
    if let Some(override_dir) = &config.cache_dir_override {
        return if probe_writable_and_executable(override_dir) {
            Ok(override_dir.clone())
        } else {
            Err(ResolutionError::CacheRootUnavailable {
                detail: format!(
                    "LUMINOSITY_CACHE_DIR {} is not writable+exec-capable",
                    override_dir.display()
                ),
            })
        };
    }

    let plugin_root = config.plugin_root.as_ref().ok_or_else(|| {
        ResolutionError::CacheRootUnavailable {
            detail: "CLAUDE_PLUGIN_ROOT is not set".to_owned(),
        }
    })?;
    let primary = plugin_root.join("bin");
    if probe_writable_and_executable(&primary) {
        return Ok(primary);
    }

    let fallback = config.xdg_fallback().ok_or_else(|| {
        ResolutionError::CacheRootUnavailable {
            detail: "plugin root is not writable+exec and no XDG/HOME is set"
                .to_owned(),
        }
    })?;
    if probe_writable_and_executable(&fallback) {
        return Ok(fallback);
    }
    Err(ResolutionError::CacheRootUnavailable {
        detail: format!(
            "neither the plugin root nor {} is writable+exec-capable",
            fallback.display()
        ),
    })
}

/// Probe a directory for both writability and exec-capability by writing a
/// trivial script and executing it — catching `noexec` mounts, which a
/// write-only probe would miss.
fn probe_writable_and_executable(dir: &Path) -> bool {
    if std::fs::create_dir_all(dir).is_err() {
        return false;
    }
    let probe = dir.join(format!(".luminosity-probe-{}", std::process::id()));
    let written = std::fs::write(&probe, b"#!/bin/sh\nexit 0\n").is_ok()
        && make_executable(&probe);
    let executable = written
        && Command::new(&probe)
            .status()
            .map(|status| status.success())
            .unwrap_or(false);
    let _ = std::fs::remove_file(&probe);
    executable
}

#[cfg(unix)]
fn make_executable(path: &Path) -> bool {
    use std::os::unix::fs::PermissionsExt as _;
    std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o755))
        .is_ok()
}

#[cfg(not(unix))]
fn make_executable(_path: &Path) -> bool {
    true
}

#[cfg(test)]
mod tests {
    use std::error::Error;
    use std::path::PathBuf;

    use super::{resolve, CacheRootConfig};

    fn config() -> CacheRootConfig {
        CacheRootConfig {
            cache_dir_override: None,
            plugin_root: None,
            xdg_cache_home: None,
            home: None,
        }
    }

    #[test]
    fn unset_plugin_root_with_no_override_is_a_named_error() {
        let result = resolve(&config());
        assert!(result.is_err(), "expected a CLAUDE_PLUGIN_ROOT error");
        if let Err(error) = result {
            assert!(error.to_string().contains("CLAUDE_PLUGIN_ROOT"));
        }
    }

    #[test]
    fn a_writable_plugin_root_is_used() -> Result<(), Box<dyn Error>> {
        let temp = tempdir()?;
        let resolved = resolve(&CacheRootConfig {
            plugin_root: Some(temp.clone()),
            ..config()
        })?;
        assert_eq!(resolved, temp.join("bin"));
        Ok(())
    }

    #[test]
    fn a_read_only_plugin_root_falls_back_to_xdg() -> Result<(), Box<dyn Error>>
    {
        use std::os::unix::fs::PermissionsExt as _;
        let plugin_root = tempdir()?;
        std::fs::create_dir_all(plugin_root.join("bin"))?;
        std::fs::set_permissions(
            plugin_root.join("bin"),
            std::fs::Permissions::from_mode(0o555),
        )?;
        let xdg = tempdir()?;
        let resolved = resolve(&CacheRootConfig {
            plugin_root: Some(plugin_root),
            xdg_cache_home: Some(xdg.clone()),
            ..config()
        })?;
        assert_eq!(resolved, xdg.join("luminosity"));
        Ok(())
    }

    #[test]
    fn an_override_is_honoured() -> Result<(), Box<dyn Error>> {
        let temp = tempdir()?;
        let resolved = resolve(&CacheRootConfig {
            cache_dir_override: Some(temp.clone()),
            ..config()
        })?;
        assert_eq!(resolved, temp);
        Ok(())
    }

    // A minimal unique temp dir under CARGO_TARGET_TMPDIR (no dev-dep needed).
    fn tempdir() -> Result<PathBuf, Box<dyn Error>> {
        use std::sync::atomic::{AtomicU64, Ordering};
        static COUNTER: AtomicU64 = AtomicU64::new(0);
        let base = std::env::temp_dir();
        let unique = format!(
            "cacheroot-{}-{}",
            std::process::id(),
            COUNTER.fetch_add(1, Ordering::Relaxed)
        );
        let dir = base.join(unique);
        std::fs::create_dir_all(&dir)?;
        Ok(dir)
    }
}
