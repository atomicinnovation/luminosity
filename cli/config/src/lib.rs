//! The configuration domain core: the value objects, the driven ports and the
//! driving ports, the precedence resolution and nested-path walk/insert that the
//! config service performs, and the two-level assembly any `.luminosity`
//! document's context block is built by.
//!
//! Depends on no infrastructure — no serde, YAML, or filesystem crate enters its
//! closure. Serialization and I/O live in the `config-adapters` crate; the core
//! speaks only in terms of the typed [`Node`] tree it is handed, and names a
//! document only by its [`ContextSource`].

pub mod context;
pub mod error;
pub mod key;
pub mod level;
pub mod node;
pub mod service;
pub mod source;

pub use context::{
    AssembleContext, AssembledContext, Assembly, ContextAssembler, LevelBody,
    LevelContribution, ReadContextBody, SourceLocation,
};
pub use error::{ConfigError, Existing};
pub use key::Key;
pub use level::Level;
pub use node::{Mapping, Node, Scalar};
pub use service::{
    ConfigAccess, ConfigService, ReadConfigLevel, Resolved, WriteConfigLevel,
};
pub use source::{ContextSource, SkillName};
