//! Bootstrap placeholder crate. The real hexagonal `version` subcommand
//! replaces this in story 0007; it exists now only so the format, lint, test,
//! and coverage toolchain has real code (with a branch) to exercise.

/// Names a release channel from whether it is a prerelease.
#[must_use]
pub const fn describe_release(prerelease: bool) -> &'static str {
    if prerelease {
        "prerelease"
    } else {
        "stable"
    }
}

#[cfg(test)]
mod tests {
    use super::describe_release;

    #[test]
    fn describes_a_stable_release() {
        assert_eq!(describe_release(false), "stable");
    }

    #[test]
    fn describes_a_prerelease() {
        assert_eq!(describe_release(true), "prerelease");
    }
}
