//! The `config` subcommand's inbound (driving) adapter.
//!
//! The domain core lives in the `config` crate; this module owns only the
//! clap-to-core mapping and the presentation of a resolved value to stdout.

pub mod inbound;
