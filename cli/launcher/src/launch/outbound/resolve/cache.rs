//! On-disk binary cache keyed by name + version + checksum.
//!
//! The checksum is in the entry name, so a cache hit needs no manifest (an
//! already-resolved binary resolves offline). Writes are atomic
//! (temp-in-dir + rename).

use std::path::{Path, PathBuf};

use crate::launch::core::ResolutionError;

pub struct CachedBinary {
    pub path: PathBuf,
    pub sha256: String,
    pub signature_path: PathBuf,
}

fn is_sha256_hex(candidate: &str) -> bool {
    candidate.len() == 64 && candidate.bytes().all(|b| b.is_ascii_hexdigit())
}

fn stem(name: &str, version: &str, sha256: &str) -> String {
    format!("{name}-{version}-{sha256}")
}

fn signature_name(stem: &str) -> String {
    format!("{stem}.minisig")
}

fn cache_error(path: &Path, error: &std::io::Error) -> ResolutionError {
    ResolutionError::Cache {
        path: path.to_path_buf(),
        detail: error.to_string(),
    }
}

#[must_use]
pub fn find(root: &Path, name: &str, version: &str) -> Option<CachedBinary> {
    let prefix = format!("{name}-{version}-");
    let entries = std::fs::read_dir(root).ok()?;
    for entry in entries.flatten() {
        let file_name = entry.file_name();
        let file = file_name.to_str()?;
        let Some(sha) = file.strip_prefix(&prefix) else {
            continue;
        };
        if !is_sha256_hex(sha) {
            continue;
        }
        let signature_path = root.join(signature_name(file));
        if signature_path.exists() {
            return Some(CachedBinary {
                path: entry.path(),
                sha256: sha.to_owned(),
                signature_path,
            });
        }
    }
    None
}

/// Atomically store a verified binary + signature. The caller MUST have
/// verified `bytes` before calling — only verified bytes reach the cache.
///
/// # Errors
///
/// [`ResolutionError::Cache`] on any IO failure.
pub fn store(
    root: &Path,
    name: &str,
    version: &str,
    sha256: &str,
    bytes: &[u8],
    signature: &str,
) -> Result<CachedBinary, ResolutionError> {
    std::fs::create_dir_all(root).map_err(|e| cache_error(root, &e))?;
    let stem = stem(name, version, sha256);
    let final_path = root.join(&stem);
    let signature_path = root.join(signature_name(&stem));

    // Temp files live inside the cache dir so the rename is intra-filesystem
    // (a cross-mount rename fails EXDEV).
    let unique = std::process::id();
    let temp_binary = root.join(format!(".tmp-{stem}-{unique}"));
    let temp_signature = root.join(format!(".tmp-{stem}-{unique}.minisig"));

    write_then_rename(&temp_binary, &final_path, bytes, true)?;
    write_then_rename(
        &temp_signature,
        &signature_path,
        signature.as_bytes(),
        false,
    )?;

    Ok(CachedBinary {
        path: final_path,
        sha256: sha256.to_owned(),
        signature_path,
    })
}

fn write_then_rename(
    temp: &Path,
    final_path: &Path,
    bytes: &[u8],
    executable: bool,
) -> Result<(), ResolutionError> {
    std::fs::write(temp, bytes).map_err(|e| cache_error(temp, &e))?;
    if executable {
        set_executable(temp)?;
    }
    std::fs::rename(temp, final_path).map_err(|e| {
        let _ = std::fs::remove_file(temp);
        cache_error(final_path, &e)
    })
}

#[cfg(unix)]
fn set_executable(path: &Path) -> Result<(), ResolutionError> {
    use std::os::unix::fs::PermissionsExt as _;
    std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o755))
        .map_err(|e| cache_error(path, &e))
}

#[cfg(not(unix))]
fn set_executable(_path: &Path) -> Result<(), ResolutionError> {
    Ok(())
}

pub fn evict(binary: &CachedBinary) {
    let _ = std::fs::remove_file(&binary.path);
    let _ = std::fs::remove_file(&binary.signature_path);
}

/// Bound cache growth for `name` to at most `cap` retained versions, removing
/// the oldest by mtime. Best-effort; never removes the newest entry.
pub fn enforce_retention_cap(root: &Path, name: &str, cap: usize) {
    let prefix = format!("{name}-");
    let Ok(entries) = std::fs::read_dir(root) else {
        return;
    };
    let mut binaries: Vec<(std::time::SystemTime, PathBuf, PathBuf)> =
        Vec::new();
    for entry in entries.flatten() {
        let file_name = entry.file_name();
        let Some(file) = file_name.to_str() else {
            continue;
        };
        let Some(rest) = file.strip_prefix(&prefix) else {
            continue;
        };
        let Some((_, sha)) = rest.rsplit_once('-') else {
            continue;
        };
        if !is_sha256_hex(sha) {
            continue;
        }
        let modified = entry
            .metadata()
            .and_then(|m| m.modified())
            .unwrap_or(std::time::UNIX_EPOCH);
        binaries.push((
            modified,
            entry.path(),
            root.join(signature_name(file)),
        ));
    }
    if binaries.len() <= cap {
        return;
    }
    binaries.sort_by_key(|(modified, _, _)| *modified);
    let remove_count = binaries.len() - cap;
    for (_, binary, signature) in binaries.into_iter().take(remove_count) {
        let _ = std::fs::remove_file(&binary);
        let _ = std::fs::remove_file(&signature);
    }
}

#[cfg(test)]
mod tests {
    use std::error::Error;
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU64, Ordering};

    use super::{enforce_retention_cap, find, store};

    static COUNTER: AtomicU64 = AtomicU64::new(0);

    fn tempdir() -> Result<PathBuf, Box<dyn Error>> {
        let dir = std::env::temp_dir().join(format!(
            "cache-{}-{}",
            std::process::id(),
            COUNTER.fetch_add(1, Ordering::Relaxed)
        ));
        std::fs::create_dir_all(&dir)?;
        Ok(dir)
    }

    const SHA: &str =
        "0000000000000000000000000000000000000000000000000000000000000000";

    #[test]
    fn store_then_find_round_trips() -> Result<(), Box<dyn Error>> {
        let root = tempdir()?;
        store(&root, "foo", "1.0.0", SHA, b"binary", "sig")?;
        let found = find(&root, "foo", "1.0.0").ok_or("not found")?;
        assert_eq!(found.sha256, SHA);
        assert_eq!(std::fs::read(&found.path)?, b"binary");
        assert!(found.signature_path.exists());
        Ok(())
    }

    #[test]
    fn find_ignores_an_entry_missing_its_signature(
    ) -> Result<(), Box<dyn Error>> {
        let root = tempdir()?;
        std::fs::write(root.join(format!("foo-1.0.0-{SHA}")), b"x")?;
        assert!(find(&root, "foo", "1.0.0").is_none());
        Ok(())
    }

    #[test]
    fn retention_cap_removes_the_oldest() -> Result<(), Box<dyn Error>> {
        let root = tempdir()?;
        let shas = [
            "1111111111111111111111111111111111111111111111111111111111111111",
            "2222222222222222222222222222222222222222222222222222222222222222",
            "3333333333333333333333333333333333333333333333333333333333333333",
        ];
        for (index, sha) in shas.iter().enumerate() {
            store(&root, "foo", &format!("1.0.{index}"), sha, b"x", "sig")?;
            // Stagger mtimes so "oldest" is deterministic.
            std::thread::sleep(std::time::Duration::from_millis(10));
        }
        enforce_retention_cap(&root, "foo", 2);
        assert!(find(&root, "foo", "1.0.0").is_none(), "oldest kept");
        assert!(find(&root, "foo", "1.0.2").is_some(), "newest evicted");
        Ok(())
    }
}
