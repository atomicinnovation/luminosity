//! The `context` subcommand's inbound (driving) adapter.
//!
//! The assembly core lives in the `config` crate; this module owns only the
//! byte-exact block each document source renders as, the empty-output policy,
//! and the per-level `--explain` diagnostic.

pub mod inbound;
