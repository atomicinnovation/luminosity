//! The `instructions` subcommand's inbound (driving) adapter.
//!
//! The assembly core lives in the `config` crate; this module owns only the
//! byte-exact `## Additional Instructions` block, the empty-output policy, and
//! the per-level `--explain` diagnostic for the one skill-instructions source.

pub mod inbound;
