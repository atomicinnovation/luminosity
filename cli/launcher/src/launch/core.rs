//! The launcher's dispatch/resolution core and the ports it speaks through.

use std::ffi::OsString;
use std::fmt;
use std::fmt::Display;
use std::fmt::Formatter;
use std::path::Path;
use std::path::PathBuf;

/// Both fields are [`OsString`] so a non-UTF-8 argument survives verbatim to the
/// exec'd child; the name is consumed for resolution, not forwarded.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExternalCommand {
    pub name: OsString,
    pub args: Vec<OsString>,
}

impl ExternalCommand {
    /// # Errors
    ///
    /// [`ResolutionError::EmptyCommand`] if the vector is empty.
    pub fn from_raw(raw: Vec<OsString>) -> Result<Self, ResolutionError> {
        let mut parts = raw.into_iter();
        let name = parts.next().ok_or(ResolutionError::EmptyCommand)?;
        Ok(Self {
            name,
            args: parts.collect(),
        })
    }
}

#[derive(Debug)]
pub enum ResolutionError {
    EmptyCommand,
    Unresolved {
        name: OsString,
    },
    Fetch {
        target: String,
        url: String,
    },
    AssetNotFound {
        target: String,
        url: String,
    },
    ReleaseUnavailable {
        target: String,
        url: String,
    },
    ChecksumMismatch {
        asset: String,
        expected: String,
        actual: String,
    },
    SignatureMismatch {
        asset: String,
    },
    ManifestSignature,
    /// Anti-rollback: a valid signature proves authenticity, not freshness.
    ManifestVersionMismatch {
        expected: String,
        actual: String,
    },
    UnsupportedSchema {
        found: u64,
        supported: u64,
    },
    Cache {
        path: PathBuf,
        detail: String,
    },
    CacheRootUnavailable {
        detail: String,
    },
    Exec {
        program: PathBuf,
        source: std::io::Error,
    },
}

impl Display for ResolutionError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyCommand => {
                write!(formatter, "no external subcommand was given")
            }
            Self::Unresolved { name } => write!(
                formatter,
                "could not resolve subcommand '{}' to a binary",
                name.to_string_lossy()
            ),
            Self::Fetch { target, url } => write!(
                formatter,
                "could not fetch the {target} asset from {url}"
            ),
            Self::AssetNotFound { target, url } => write!(
                formatter,
                "no {target} asset published at {url}"
            ),
            Self::ReleaseUnavailable { target, url } => write!(
                formatter,
                "the release for the {target} asset is unavailable at {url}"
            ),
            Self::ChecksumMismatch {
                asset,
                expected,
                actual,
            } => write!(
                formatter,
                "{asset}: sha256 mismatch (expected {expected}, got {actual})"
            ),
            Self::SignatureMismatch { asset } => write!(
                formatter,
                "{asset}: minisign signature is not valid for any trusted key"
            ),
            Self::ManifestSignature => write!(
                formatter,
                "the release manifest signature is not valid for any trusted key"
            ),
            Self::ManifestVersionMismatch { expected, actual } => write!(
                formatter,
                "manifest version {actual} does not match expected {expected}"
            ),
            Self::UnsupportedSchema { found, supported } => write!(
                formatter,
                "unsupported manifest schema_version {found} (supported \
                 up to {supported})"
            ),
            Self::Cache { path, detail } => {
                write!(formatter, "cache error at {}: {detail}", path.display())
            }
            Self::CacheRootUnavailable { detail } => {
                write!(formatter, "no usable cache directory: {detail}")
            }
            Self::Exec { program, source } => {
                write!(
                    formatter,
                    "failed to exec {}: {source}",
                    program.display()
                )
            }
        }
    }
}

impl std::error::Error for ResolutionError {}

impl From<ResolutionError> for kernel::Error {
    fn from(error: ResolutionError) -> Self {
        Self::Failed(error.to_string())
    }
}

pub trait ResolveBinary {
    /// # Errors
    ///
    /// A [`ResolutionError`] when the binary cannot be produced.
    fn resolve(
        &self,
        command: &ExternalCommand,
    ) -> Result<PathBuf, ResolutionError>;
}

/// A port so dispatch's resolve→exec wiring is unit-testable with a fake; a real
/// Unix `exec` cannot be tested in-process (it would replace the test runner).
pub trait ExecBinary {
    /// Returns only on failure — a successful `exec` replaces the process.
    fn exec(&self, program: &Path, args: &[OsString]) -> ResolutionError;
}

/// Only ever returns an error — a successful `exec` replaces this process.
pub fn run_external(
    resolver: &impl ResolveBinary,
    executor: &impl ExecBinary,
    command: &ExternalCommand,
) -> ResolutionError {
    match resolver.resolve(command) {
        Ok(program) => executor.exec(&program, &command.args),
        Err(error) => error,
    }
}

#[cfg(test)]
mod tests {
    use std::cell::RefCell;
    use std::error::Error;
    use std::ffi::OsString;
    use std::path::{Path, PathBuf};

    use super::{
        run_external, ExecBinary, ExternalCommand, ResolutionError,
        ResolveBinary,
    };

    fn command(name: &str, args: &[&str]) -> ExternalCommand {
        ExternalCommand {
            name: OsString::from(name),
            args: args.iter().map(OsString::from).collect(),
        }
    }

    struct FixedResolver {
        path: PathBuf,
    }

    impl ResolveBinary for FixedResolver {
        fn resolve(
            &self,
            _command: &ExternalCommand,
        ) -> Result<PathBuf, ResolutionError> {
            Ok(self.path.clone())
        }
    }

    struct FailingResolver;

    impl ResolveBinary for FailingResolver {
        fn resolve(
            &self,
            command: &ExternalCommand,
        ) -> Result<PathBuf, ResolutionError> {
            Err(ResolutionError::Unresolved {
                name: command.name.clone(),
            })
        }
    }

    #[derive(Default)]
    struct RecordingExec {
        seen: RefCell<Option<(PathBuf, Vec<OsString>)>>,
    }

    impl ExecBinary for RecordingExec {
        fn exec(&self, program: &Path, args: &[OsString]) -> ResolutionError {
            *self.seen.borrow_mut() =
                Some((program.to_path_buf(), args.to_vec()));
            ResolutionError::Exec {
                program: program.to_path_buf(),
                source: std::io::Error::other("fake exec"),
            }
        }
    }

    #[test]
    fn from_raw_splits_name_from_forwarded_args() -> Result<(), Box<dyn Error>>
    {
        let parsed = ExternalCommand::from_raw(vec![
            OsString::from("foo"),
            OsString::from("--flag"),
            OsString::from("value"),
        ])?;
        assert_eq!(parsed.name, OsString::from("foo"));
        assert_eq!(
            parsed.args,
            vec![OsString::from("--flag"), OsString::from("value")]
        );
        Ok(())
    }

    #[test]
    fn from_raw_rejects_an_empty_vector() {
        assert!(matches!(
            ExternalCommand::from_raw(vec![]),
            Err(ResolutionError::EmptyCommand)
        ));
    }

    #[test]
    fn run_external_execs_the_resolved_path_with_forwarded_args(
    ) -> Result<(), Box<dyn Error>> {
        let resolver = FixedResolver {
            path: PathBuf::from("/cache/luminosity-foo"),
        };
        let executor = RecordingExec::default();
        let _ = run_external(
            &resolver,
            &executor,
            &command("foo", ["a", "b"].as_slice()),
        );
        let seen = executor.seen.borrow();
        let (program, args) = seen.as_ref().ok_or("exec was not attempted")?;
        assert_eq!(program, &PathBuf::from("/cache/luminosity-foo"));
        assert_eq!(args, &vec![OsString::from("a"), OsString::from("b")]);
        Ok(())
    }

    #[test]
    fn run_external_returns_the_resolve_error_without_exec() {
        let executor = RecordingExec::default();
        let error =
            run_external(&FailingResolver, &executor, &command("foo", &[]));
        assert!(matches!(error, ResolutionError::Unresolved { .. }));
        assert!(executor.seen.borrow().is_none(), "exec must not run");
    }

    #[test]
    fn resolution_error_maps_into_a_kernel_failed_diagnostic() {
        let error = ResolutionError::Unresolved {
            name: OsString::from("frobnicate"),
        };
        let kernel_error: kernel::Error = error.into();
        assert!(kernel_error.to_string().contains("frobnicate"));
    }
}
