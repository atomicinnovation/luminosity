//! Manifest-driven help synthesis: `luminosity --help` augments clap's built-in
//! help with a section built from the signed manifest's per-binary descriptions.

use std::fmt::Write as _;

use crate::launch::outbound::resolve::manifest::Manifest;

/// Descriptions are terminal-rendered, so control/escape characters are stripped
/// to defend against terminal-escape injection.
#[must_use]
pub fn external_subcommands_section(manifest: &Manifest) -> Option<String> {
    if manifest.binaries.is_empty() {
        return None;
    }
    let width = manifest
        .binaries
        .keys()
        .map(|name| sanitize(name).len())
        .max()
        .unwrap_or(0);
    let mut section = String::from("External subcommands:");
    for (name, entry) in &manifest.binaries {
        let name = sanitize(name);
        let description = sanitize(&entry.description);
        let _ = write!(section, "\n  {name:<width$}  {description}");
    }
    Some(section)
}

fn sanitize(text: &str) -> String {
    text.chars().filter(|c| !c.is_control()).collect()
}

#[cfg(test)]
mod tests {
    use std::error::Error;

    use crate::launch::outbound::resolve::manifest::Manifest;

    use super::{external_subcommands_section, sanitize};

    fn manifest(json: &str) -> Result<Manifest, Box<dyn Error>> {
        Ok(Manifest::parse_and_validate(json.as_bytes(), "1.0.0")?)
    }

    #[test]
    fn renders_a_line_matching_the_name_and_description(
    ) -> Result<(), Box<dyn Error>> {
        let manifest = manifest(
            "{\"schema_version\":1,\"version\":\"1.0.0\",\"binaries\":{\
             \"foo\":{\"description\":\"Bar tool\",\"platforms\":{}}}}",
        )?;
        let section = external_subcommands_section(&manifest)
            .ok_or("expected section")?;
        assert!(section.contains("foo"));
        assert!(section.contains("Bar tool"));
        Ok(())
    }

    #[test]
    fn no_binaries_yields_no_section() -> Result<(), Box<dyn Error>> {
        let manifest = manifest(
            "{\"schema_version\":1,\"version\":\"1.0.0\",\"binaries\":{}}",
        )?;
        assert!(external_subcommands_section(&manifest).is_none());
        Ok(())
    }

    #[test]
    fn strips_control_and_escape_sequences_but_keeps_printable_text() {
        let dirty = "safe\u{1b}[31m text\u{0007}here";
        let clean = sanitize(dirty);
        assert!(!clean.contains('\u{1b}'));
        assert!(!clean.contains('\u{0007}'));
        assert!(clean.contains("safe"));
        assert!(clean.contains("text"));
        assert!(clean.contains("here"));
    }
}
