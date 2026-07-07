//! The configuration domain core: the value objects, the two driven ports and
//! the driving port, and the precedence resolution and nested-path walk/insert
//! that the application service performs.
//!
//! Depends on no infrastructure — no serde, YAML, or filesystem crate enters its
//! closure. Serialization and I/O live in the `config-adapters` crate; the core
//! speaks only in terms of the typed [`Node`] tree it is handed.

pub mod error;
pub mod key;
pub mod level;
pub mod node;
pub mod service;

pub use error::{ConfigError, Existing};
pub use key::Key;
pub use level::Level;
pub use node::{Mapping, Node, Scalar};
pub use service::{
    ConfigAccess, ConfigService, ReadConfigLevel, Resolved, WriteConfigLevel,
};
