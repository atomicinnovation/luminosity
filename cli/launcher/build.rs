//! Emits the `version` build metadata via vergen and copies the release public
//! key into `OUT_DIR` for the launcher to embed.
//!
//! vergen deliberately degrades a git-less or shallow build to a placeholder
//! rather than failing. The key copy, by contrast, fails the build loudly — a
//! launcher that cannot embed its trust root must not build.

use std::error::Error;
use std::path::Path;

use vergen_gitcl::{BuildBuilder, CargoBuilder, Emitter, GitclBuilder};

const SHORT_SHA: bool = false;

fn main() -> Result<(), Box<dyn Error>> {
    embed_release_public_key()?;

    let build = BuildBuilder::default().build_timestamp(true).build()?;
    let cargo = CargoBuilder::default().target_triple(true).build()?;
    let gitcl = GitclBuilder::default().sha(SHORT_SHA).build()?;
    Emitter::default()
        .add_instructions(&build)?
        .add_instructions(&cargo)?
        .add_instructions(&gitcl)?
        .emit()?;
    Ok(())
}

fn embed_release_public_key() -> Result<(), Box<dyn Error>> {
    let manifest_dir = std::env::var("CARGO_MANIFEST_DIR")?;
    let source =
        Path::new(&manifest_dir).join("../../keys/luminosity-release.pub");
    let out_dir = std::env::var("OUT_DIR")?;
    let destination = Path::new(&out_dir).join("release.pub");

    let key = std::fs::read(&source).map_err(|error| {
        format!(
            "cannot read the release public key at {}: {error}",
            source.display()
        )
    })?;
    std::fs::write(&destination, key)?;
    println!("cargo:rerun-if-changed={}", source.display());
    Ok(())
}
