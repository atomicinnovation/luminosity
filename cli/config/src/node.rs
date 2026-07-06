//! The typed, order-preserving configuration tree.
//!
//! [`Node`] distinguishes scalars, sequences, and mappings; [`Scalar`] retains
//! the value's type; [`Mapping`] retains insertion order. Together they let a
//! whole-document rewrite preserve every untouched sibling's type and the key
//! order, so a `set` neither coerces a sibling nor alphabetises keys.

/// A value in the configuration tree.
#[derive(Debug, Clone, PartialEq)]
pub enum Node {
    Scalar(Scalar),
    Sequence(Vec<Node>),
    Mapping(Mapping),
}

/// A leaf value, typed so a rewrite keeps a sibling's kind intact.
#[derive(Debug, Clone, PartialEq)]
pub enum Scalar {
    String(String),
    Bool(bool),
    Int(i64),
    Float(f64),
    Null,
}

/// An insertion-ordered mapping. A `Vec` rather than a `BTreeMap` so keys keep
/// their order and no ordered-map crate enters the core's closure.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct Mapping(Vec<(String, Node)>);

impl Mapping {
    #[must_use]
    pub const fn new() -> Self {
        Self(Vec::new())
    }

    #[must_use]
    pub fn get(&self, key: &str) -> Option<&Node> {
        self.0
            .iter()
            .find(|(existing, _)| existing == key)
            .map(|(_, node)| node)
    }

    pub fn get_mut(&mut self, key: &str) -> Option<&mut Node> {
        self.0
            .iter_mut()
            .find(|(existing, _)| existing == key)
            .map(|(_, node)| node)
    }

    /// Replaces the value at `key` in place, or appends it if absent, so an
    /// existing key keeps its position.
    pub fn upsert(&mut self, key: &str, node: Node) {
        match self.0.iter_mut().find(|(existing, _)| existing == key) {
            Some((_, slot)) => *slot = node,
            None => self.0.push((key.to_owned(), node)),
        }
    }

    pub fn push(&mut self, key: String, node: Node) {
        self.0.push((key, node));
    }

    #[must_use]
    pub fn entries(&self) -> &[(String, Node)] {
        &self.0
    }
}

impl FromIterator<(String, Node)> for Mapping {
    fn from_iter<I: IntoIterator<Item = (String, Node)>>(iter: I) -> Self {
        Self(iter.into_iter().collect())
    }
}
