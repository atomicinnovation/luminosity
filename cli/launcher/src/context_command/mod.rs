//! The `context` subcommand's inbound (driving) adapter.
//!
//! The assembly core lives in the `config` crate; this module owns only the
//! byte-exact `## Project Context` block, the empty-output policy, and the
//! per-level `--explain` diagnostic.

pub mod inbound;
