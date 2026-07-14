//! The filesystem store: it roots every `.luminosity` document at a discovered
//! project directory and implements the core's read/write ports over `std::fs`.
//!
//! It owns the whole path rule — which file a `(ContextSource, Level)` pair
//! names — so no caller ever composes `skills/<name>/<file>` itself, and the two
//! rules that guard a free-form context file: containment (a symlinked file or
//! directory component whose target escapes `.luminosity/` is refused, never
//! followed) and the mapping-only frontmatter strip (a `---` fence is stripped
//! only when it parses as a YAML mapping, so prose opening with a thematic break
//! is never silently truncated).

use std::fs;
use std::io::ErrorKind;
use std::path::{Path, PathBuf};
use std::process;
use std::sync::atomic::{AtomicU64, Ordering};

use config::{
    ConfigError, ContextSource, Level, LevelBody, Node, ReadConfigLevel,
    ReadContextBody, SourceLocation, WriteConfigLevel,
};

use crate::document;
use crate::frontmatter::{self, Split};

static WRITE_COUNTER: AtomicU64 = AtomicU64::new(0);

/// A config store rooted at a project directory. Holds only its root path, so
/// it is a cheap `Clone` that can back both read and write ports.
#[derive(Clone)]
pub struct FileConfigStore {
    root: PathBuf,
}

impl FileConfigStore {
    pub fn rooted_at(root: impl Into<PathBuf>) -> Self {
        Self { root: root.into() }
    }

    /// Roots at the nearest ancestor of `start_dir` holding a `.luminosity/`
    /// directory or a `.git` entry, else at `start_dir`. A single upward walk,
    /// so an enclosing `.git` bounds it — discovery never crosses a repo
    /// boundary to root above a nested repo.
    #[must_use]
    pub fn discover(start_dir: &Path) -> Self {
        Self {
            root: discover_root(start_dir),
        }
    }

    fn config_dir(&self) -> PathBuf {
        self.root.join(".luminosity")
    }

    fn config_path(&self, level: Level) -> PathBuf {
        self.config_dir()
            .join(format!("config{}.md", level.qualifier()))
    }

    fn context_path(&self, source: &ContextSource, level: Level) -> PathBuf {
        match source {
            ContextSource::Project => self.config_path(level),
            ContextSource::Skill(name) => self
                .config_dir()
                .join("skills")
                .join(name.as_str())
                .join(format!("context{}.md", level.qualifier())),
        }
    }

    fn relative(&self, path: &Path) -> String {
        display(path.strip_prefix(&self.root).unwrap_or(path))
    }

    /// Reads a free-form context body: the content below a frontmatter fence
    /// that parses as a YAML mapping, else the whole file.
    ///
    /// A terminated fence whose content is a non-mapping scalar (a prose
    /// thematic break, or malformed YAML) is body, not frontmatter — so the
    /// whole file is returned, byte-for-byte as read. Only an *unterminated*
    /// fence fails loud.
    fn read_context_body(
        &self,
        path: &Path,
    ) -> Result<Option<String>, ConfigError> {
        self.refuse_escaping_path(path)?;
        let Some((content, split)) = read_and_split(path)? else {
            return Ok(None);
        };
        let frontmatter_is_a_mapping = matches!(
            document::parse_frontmatter(&split.frontmatter),
            Ok(Node::Mapping(_))
        );
        Ok(Some(if frontmatter_is_a_mapping {
            split.body
        } else {
            content
        }))
    }

    /// Refuses a path whose parent directory or whose symlinked leaf resolves
    /// outside `.luminosity/`.
    ///
    /// Both sides are canonicalised before the component-wise comparison: a
    /// string prefix would admit a `.luminosity-evil/` sibling, and comparing a
    /// canonical file against a raw root would refuse every legitimate file
    /// under a symlinked root (macOS `/tmp` → `/private/tmp`).
    fn refuse_escaping_path(&self, path: &Path) -> Result<(), ConfigError> {
        let Some(root) = canonical(&self.config_dir())? else {
            return Ok(());
        };
        let escapes = |resolved: &Path| !resolved.starts_with(&root);
        if let Some(parent) = path.parent() {
            if canonical(parent)?.as_deref().is_some_and(escapes) {
                return Err(unsafe_path(path));
            }
        }
        if is_symlink(path)? && canonical(path)?.as_deref().is_some_and(escapes)
        {
            return Err(unsafe_path(path));
        }
        Ok(())
    }

    fn atomic_write(
        &self,
        target: &Path,
        contents: &str,
    ) -> Result<(), ConfigError> {
        let temp_dir = self.config_dir().join("tmp");
        fs::create_dir_all(&temp_dir)
            .map_err(|error| io_error(&temp_dir, &error))?;
        let temp = temp_dir.join(format!(
            "config-{}-{}.tmp",
            process::id(),
            WRITE_COUNTER.fetch_add(1, Ordering::Relaxed)
        ));
        if let Err(error) = fs::write(&temp, contents) {
            let _ = fs::remove_file(&temp);
            return Err(io_error(&temp, &error));
        }
        if let Err(error) = fs::rename(&temp, target) {
            let _ = fs::remove_file(&temp);
            return Err(io_error(target, &error));
        }
        Ok(())
    }
}

impl ReadConfigLevel for FileConfigStore {
    fn read(&self, level: Level) -> Result<Option<Node>, ConfigError> {
        let path = self.config_path(level);
        let Some((_, split)) = read_and_split(&path)? else {
            return Ok(None);
        };
        let node = document::parse_frontmatter(&split.frontmatter).map_err(
            |detail| ConfigError::MalformedFrontmatter {
                path: display(&path),
                detail,
            },
        )?;
        Ok(Some(node))
    }
}

impl ReadContextBody for FileConfigStore {
    fn read_body(
        &self,
        source: &ContextSource,
        level: Level,
    ) -> Result<LevelBody, ConfigError> {
        let path = self.context_path(source, level);
        Ok(LevelBody {
            path: self.relative(&path),
            body: self.read_context_body(&path)?,
        })
    }

    fn locate(
        &self,
        source: &ContextSource,
    ) -> Result<SourceLocation, ConfigError> {
        Ok(SourceLocation {
            root: display(&self.root),
            paths: [Level::Team, Level::Personal]
                .map(|level| self.relative(&self.context_path(source, level))),
        })
    }
}

impl WriteConfigLevel for FileConfigStore {
    fn write(&self, level: Level, document: &Node) -> Result<(), ConfigError> {
        let path = self.config_path(level);
        let existing = match fs::read_to_string(&path) {
            Ok(content) => Some(content),
            Err(error) if error.kind() == ErrorKind::NotFound => None,
            Err(error) => return Err(io_error(&path, &error)),
        };
        let rendered = document::render(existing.as_deref(), document)
            .map_err(|detail| ConfigError::MalformedFrontmatter {
                path: display(&path),
                detail,
            })?;
        self.atomic_write(&path, &rendered)
    }
}

/// Reads a file and splits it at its frontmatter fences, retaining the raw
/// content a caller may prefer over a reconstruction of the split.
fn read_and_split(path: &Path) -> Result<Option<(String, Split)>, ConfigError> {
    let content = match fs::read_to_string(path) {
        Ok(content) => content,
        Err(error) if error.kind() == ErrorKind::NotFound => return Ok(None),
        Err(error) => return Err(io_error(path, &error)),
    };
    let split = frontmatter::split(&content).map_err(|detail| {
        ConfigError::MalformedFrontmatter {
            path: display(path),
            detail,
        }
    })?;
    Ok(Some((content, split)))
}

fn canonical(path: &Path) -> Result<Option<PathBuf>, ConfigError> {
    match fs::canonicalize(path) {
        Ok(resolved) => Ok(Some(resolved)),
        Err(error) if error.kind() == ErrorKind::NotFound => Ok(None),
        Err(error) => Err(io_error(path, &error)),
    }
}

fn is_symlink(path: &Path) -> Result<bool, ConfigError> {
    match fs::symlink_metadata(path) {
        Ok(metadata) => Ok(metadata.file_type().is_symlink()),
        Err(error) if error.kind() == ErrorKind::NotFound => Ok(false),
        Err(error) => Err(io_error(path, &error)),
    }
}

fn discover_root(start_dir: &Path) -> PathBuf {
    let mut ancestor = Some(start_dir);
    while let Some(dir) = ancestor {
        if dir.join(".luminosity").is_dir() || dir.join(".git").exists() {
            return dir.to_path_buf();
        }
        ancestor = dir.parent();
    }
    start_dir.to_path_buf()
}

fn display(path: &Path) -> String {
    path.display().to_string()
}

fn io_error(path: &Path, error: &std::io::Error) -> ConfigError {
    ConfigError::Io {
        path: display(path),
        detail: error.to_string(),
    }
}

fn unsafe_path(path: &Path) -> ConfigError {
    ConfigError::UnsafePath {
        path: display(path),
    }
}

#[cfg(test)]
mod tests {
    use std::fs;
    use std::path::{Path, PathBuf};
    use std::sync::atomic::{AtomicU64, Ordering};

    use config::{
        ConfigAccess, ConfigError, ConfigService, ContextSource, Key, Level,
        Node, ReadConfigLevel, ReadContextBody, Scalar, SkillName,
        WriteConfigLevel,
    };

    use super::FileConfigStore;

    type TestError = Box<dyn std::error::Error>;

    static COUNTER: AtomicU64 = AtomicU64::new(0);

    fn tempdir() -> Result<PathBuf, TestError> {
        let dir = std::env::temp_dir().join(format!(
            "cfg-adapters-{}-{}",
            std::process::id(),
            COUNTER.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir_all(&dir)?;
        Ok(dir)
    }

    fn seed(root: &Path, name: &str, content: &str) -> Result<(), TestError> {
        fs::create_dir_all(root.join(".luminosity"))?;
        fs::write(root.join(".luminosity").join(name), content)?;
        Ok(())
    }

    fn configure() -> Result<ContextSource, TestError> {
        Ok(ContextSource::Skill(SkillName::parse("configure")?))
    }

    fn skill_dir(root: &Path) -> PathBuf {
        root.join(".luminosity/skills/configure")
    }

    fn seed_skill(
        root: &Path,
        name: &str,
        content: &str,
    ) -> Result<(), TestError> {
        let dir = skill_dir(root);
        fs::create_dir_all(&dir)?;
        fs::write(dir.join(name), content)?;
        Ok(())
    }

    fn skill_body(
        root: &Path,
        level: Level,
    ) -> Result<Option<String>, TestError> {
        Ok(FileConfigStore::rooted_at(root)
            .read_body(&configure()?, level)?
            .body)
    }

    fn project_body(
        root: &Path,
        level: Level,
    ) -> Result<Option<String>, TestError> {
        Ok(FileConfigStore::rooted_at(root)
            .read_body(&ContextSource::Project, level)?
            .body)
    }

    fn service(
        store: &FileConfigStore,
    ) -> ConfigService<FileConfigStore, FileConfigStore> {
        ConfigService::new(store.clone(), store.clone())
    }

    fn scalar_at<'a>(node: &'a Node, path: &[&str]) -> Option<&'a Scalar> {
        let mut current = node;
        for segment in path {
            let Node::Mapping(mapping) = current else {
                return None;
            };
            current = mapping.get(segment)?;
        }
        match current {
            Node::Scalar(scalar) => Some(scalar),
            _ => None,
        }
    }

    fn single_mapping(key: &str, value: &str) -> Node {
        Node::Mapping(
            vec![(
                key.to_owned(),
                Node::Scalar(Scalar::String(value.to_owned())),
            )]
            .into_iter()
            .collect(),
        )
    }

    #[test]
    fn an_absent_file_reads_as_none() -> Result<(), TestError> {
        let store = FileConfigStore::rooted_at(tempdir()?);
        assert!(store.read(Level::Team)?.is_none());
        Ok(())
    }

    #[test]
    fn a_write_creates_the_dir_and_round_trips() -> Result<(), TestError> {
        let root = tempdir()?;
        let store = FileConfigStore::rooted_at(&root);
        service(&store).set(
            &Key::parse("core.example")?,
            "value",
            Level::Team,
        )?;

        assert!(root.join(".luminosity/config.md").is_file());
        let read = store.read(Level::Team)?.ok_or("expected a document")?;
        assert_eq!(
            scalar_at(&read, &["core", "example"]),
            Some(&Scalar::String("value".to_owned()))
        );
        Ok(())
    }

    #[test]
    fn a_write_preserves_the_body() -> Result<(), TestError> {
        let root = tempdir()?;
        seed(
            &root,
            "config.md",
            "---\ncore:\n  example: old\n---\nbody\n",
        )?;
        let store = FileConfigStore::rooted_at(&root);
        service(&store).set(
            &Key::parse("core.example")?,
            "new",
            Level::Team,
        )?;

        let content = fs::read_to_string(root.join(".luminosity/config.md"))?;
        assert!(content.ends_with("body\n"), "body lost: {content:?}");
        Ok(())
    }

    #[test]
    fn body_edge_cases_round_trip() -> Result<(), TestError> {
        for body in ["before\n---\nafter\n", "no trailing newline", ""] {
            let root = tempdir()?;
            seed(
                &root,
                "config.md",
                &format!("---\ncore:\n  example: old\n---\n{body}"),
            )?;
            let store = FileConfigStore::rooted_at(&root);
            service(&store).set(
                &Key::parse("core.example")?,
                "new",
                Level::Team,
            )?;
            let content =
                fs::read_to_string(root.join(".luminosity/config.md"))?;
            assert!(
                content.ends_with(body),
                "body {body:?} not preserved in {content:?}"
            );
        }
        Ok(())
    }

    #[test]
    fn a_write_preserves_a_sibling_type_and_key_order() -> Result<(), TestError>
    {
        let root = tempdir()?;
        seed(
            &root,
            "config.md",
            "---\nenabled: true\ncore:\n  example: old\nlast: 3\n---\n",
        )?;
        let store = FileConfigStore::rooted_at(&root);
        service(&store).set(
            &Key::parse("core.example")?,
            "new",
            Level::Team,
        )?;

        let read = store.read(Level::Team)?.ok_or("expected a document")?;
        let Node::Mapping(root_map) = &read else {
            return Err("root was not a mapping".into());
        };
        let names: Vec<&str> = root_map
            .entries()
            .iter()
            .map(|(name, _)| name.as_str())
            .collect();
        assert_eq!(names, ["enabled", "core", "last"]);
        assert_eq!(scalar_at(&read, &["enabled"]), Some(&Scalar::Bool(true)));
        assert_eq!(scalar_at(&read, &["last"]), Some(&Scalar::Int(3)));
        Ok(())
    }

    #[test]
    fn typed_scalars_and_a_sequence_parse() -> Result<(), TestError> {
        let root = tempdir()?;
        seed(
            &root,
            "config.md",
            "---\nflag: true\ncount: 7\nratio: 1.5\nempty:\n\
             items:\n  - a\n  - b\nbig: 10000000000000000000\n---\n",
        )?;
        let store = FileConfigStore::rooted_at(&root);
        let read = store.read(Level::Team)?.ok_or("expected a document")?;

        assert_eq!(scalar_at(&read, &["flag"]), Some(&Scalar::Bool(true)));
        assert_eq!(scalar_at(&read, &["count"]), Some(&Scalar::Int(7)));
        assert_eq!(scalar_at(&read, &["ratio"]), Some(&Scalar::Float(1.5)));
        assert_eq!(scalar_at(&read, &["empty"]), Some(&Scalar::Null));
        assert_eq!(
            scalar_at(&read, &["big"]),
            Some(&Scalar::String("10000000000000000000".to_owned()))
        );
        let Node::Mapping(map) = &read else {
            return Err("root was not a mapping".into());
        };
        assert!(matches!(map.get("items"), Some(Node::Sequence(_))));
        Ok(())
    }

    #[test]
    fn malformed_frontmatter_reads_as_malformed() -> Result<(), TestError> {
        let root = tempdir()?;
        seed(&root, "config.md", "---\nkey: value\n")?;
        let store = FileConfigStore::rooted_at(&root);
        assert!(matches!(
            store.read(Level::Team),
            Err(ConfigError::MalformedFrontmatter { .. })
        ));
        Ok(())
    }

    #[test]
    fn a_write_against_a_malformed_file_fails_closed() -> Result<(), TestError>
    {
        let root = tempdir()?;
        let malformed = "---\nkey: value\n";
        seed(&root, "config.md", malformed)?;
        let store = FileConfigStore::rooted_at(&root);
        let document = single_mapping("core", "v");

        assert!(matches!(
            store.write(Level::Team, &document),
            Err(ConfigError::MalformedFrontmatter { .. })
        ));
        assert_eq!(
            fs::read_to_string(root.join(".luminosity/config.md"))?,
            malformed
        );
        Ok(())
    }

    #[test]
    fn a_successful_write_leaves_no_stray_temp() -> Result<(), TestError> {
        let root = tempdir()?;
        let store = FileConfigStore::rooted_at(&root);
        service(&store).set(&Key::parse("core.example")?, "v", Level::Team)?;

        let temp_entries: Vec<_> = fs::read_dir(root.join(".luminosity/tmp"))?
            .flatten()
            .collect();
        assert!(temp_entries.is_empty(), "stray temp: {temp_entries:?}");
        Ok(())
    }

    #[test]
    fn read_body_returns_the_untrimmed_body() -> Result<(), TestError> {
        let root = tempdir()?;
        seed(&root, "config.md", "---\ncore: v\n---\n\n  body line\n\n")?;
        assert_eq!(
            project_body(&root, Level::Team)?,
            Some("\n  body line\n\n".to_owned())
        );
        Ok(())
    }

    #[test]
    fn an_absent_file_reads_no_body() -> Result<(), TestError> {
        assert!(project_body(&tempdir()?, Level::Team)?.is_none());
        Ok(())
    }

    #[test]
    fn a_body_only_file_returns_the_whole_content() -> Result<(), TestError> {
        let root = tempdir()?;
        seed(&root, "config.md", "no frontmatter here\n")?;
        assert_eq!(
            project_body(&root, Level::Team)?,
            Some("no frontmatter here\n".to_owned())
        );
        Ok(())
    }

    #[test]
    fn read_body_fails_loud_on_malformed_frontmatter() -> Result<(), TestError>
    {
        let root = tempdir()?;
        seed(&root, "config.md", "---\nkey: value\n")?;
        assert!(matches!(
            project_body(&root, Level::Team),
            Err(error) if matches!(
                error.downcast_ref::<ConfigError>(),
                Some(ConfigError::MalformedFrontmatter { path, .. })
                    if path.contains("config.md")
            )
        ));
        Ok(())
    }

    #[test]
    fn read_and_read_body_share_the_same_file() -> Result<(), TestError> {
        let root = tempdir()?;
        seed(
            &root,
            "config.md",
            "---\ncore:\n  example: v\n---\nbody text\n",
        )?;
        let store = FileConfigStore::rooted_at(&root);
        assert_eq!(
            scalar_at(
                &store.read(Level::Team)?.ok_or("expected a document")?,
                &["core", "example"]
            ),
            Some(&Scalar::String("v".to_owned()))
        );
        assert_eq!(
            project_body(&root, Level::Team)?,
            Some("body text\n".to_owned())
        );
        Ok(())
    }

    #[test]
    fn an_absent_skill_context_reads_as_none() -> Result<(), TestError> {
        let root = tempdir()?;
        seed(&root, "config.md", "---\ncore: v\n---\nteam\n")?;
        assert!(skill_body(&root, Level::Team)?.is_none());
        Ok(())
    }

    #[test]
    fn a_team_skill_context_reads_its_body() -> Result<(), TestError> {
        let root = tempdir()?;
        seed_skill(&root, "context.md", "skill team\n")?;
        assert_eq!(
            skill_body(&root, Level::Team)?,
            Some("skill team\n".to_owned())
        );
        Ok(())
    }

    #[test]
    fn a_personal_skill_context_reads_its_body() -> Result<(), TestError> {
        let root = tempdir()?;
        seed_skill(&root, "context.local.md", "skill personal\n")?;
        assert_eq!(
            skill_body(&root, Level::Personal)?,
            Some("skill personal\n".to_owned())
        );
        Ok(())
    }

    #[test]
    fn a_skill_context_body_strips_its_frontmatter_mapping(
    ) -> Result<(), TestError> {
        let root = tempdir()?;
        seed_skill(&root, "context.md", "---\ntitle: x\n---\nthe body\n")?;
        assert_eq!(
            skill_body(&root, Level::Team)?,
            Some("the body\n".to_owned())
        );
        Ok(())
    }

    #[test]
    fn an_empty_frontmatter_fence_is_stripped() -> Result<(), TestError> {
        let root = tempdir()?;
        seed_skill(&root, "context.md", "---\n---\nthe body\n")?;
        assert_eq!(
            skill_body(&root, Level::Team)?,
            Some("the body\n".to_owned())
        );
        Ok(())
    }

    #[test]
    fn a_skill_context_without_frontmatter_returns_the_whole_content(
    ) -> Result<(), TestError> {
        let root = tempdir()?;
        seed_skill(&root, "context.md", "just prose\n")?;
        assert_eq!(
            skill_body(&root, Level::Team)?,
            Some("just prose\n".to_owned())
        );
        Ok(())
    }

    #[test]
    fn a_skill_context_opening_with_a_thematic_break_is_preserved(
    ) -> Result<(), TestError> {
        let root = tempdir()?;
        let content = "---\nSection A\n---\nSection B\n";
        seed_skill(&root, "context.md", content)?;
        assert_eq!(skill_body(&root, Level::Team)?, Some(content.to_owned()));
        Ok(())
    }

    #[test]
    fn a_skill_context_with_non_mapping_frontmatter_is_injected_whole(
    ) -> Result<(), TestError> {
        let root = tempdir()?;
        let content = "---\n- a\n- b\n---\nbody\n";
        seed_skill(&root, "context.md", content)?;
        assert_eq!(skill_body(&root, Level::Team)?, Some(content.to_owned()));
        Ok(())
    }

    #[test]
    fn a_crlf_thematic_break_body_round_trips_byte_exact(
    ) -> Result<(), TestError> {
        let root = tempdir()?;
        let content = "---\r\nSection A\r\n---\r\nSection B\r\n";
        seed_skill(&root, "context.md", content)?;
        assert_eq!(skill_body(&root, Level::Team)?, Some(content.to_owned()));
        Ok(())
    }

    #[test]
    fn a_malformed_skill_context_fails_loud_naming_the_path(
    ) -> Result<(), TestError> {
        let root = tempdir()?;
        seed_skill(&root, "context.md", "---\nkey: value\n")?;
        assert!(matches!(
            skill_body(&root, Level::Team),
            Err(error) if matches!(
                error.downcast_ref::<ConfigError>(),
                Some(ConfigError::MalformedFrontmatter { path, .. })
                    if path.contains("skills/configure/context.md")
            )
        ));
        Ok(())
    }

    #[test]
    fn a_symlinked_skill_context_file_pointing_outside_is_refused(
    ) -> Result<(), TestError> {
        let root = tempdir()?;
        let outside = root.join("outside.md");
        fs::write(&outside, "secrets\n")?;
        fs::create_dir_all(skill_dir(&root))?;
        std::os::unix::fs::symlink(
            &outside,
            skill_dir(&root).join("context.md"),
        )?;

        assert!(matches!(
            skill_body(&root, Level::Team),
            Err(error) if matches!(
                error.downcast_ref::<ConfigError>(),
                Some(ConfigError::UnsafePath { .. })
            )
        ));
        Ok(())
    }

    #[test]
    fn a_symlinked_skill_directory_component_pointing_outside_is_refused(
    ) -> Result<(), TestError> {
        let root = tempdir()?;
        let outside = root.join("elsewhere");
        fs::create_dir_all(&outside)?;
        fs::write(outside.join("context.md"), "secrets\n")?;
        fs::create_dir_all(root.join(".luminosity/skills"))?;
        std::os::unix::fs::symlink(
            &outside,
            root.join(".luminosity/skills/configure"),
        )?;

        assert!(matches!(
            skill_body(&root, Level::Team),
            Err(error) if matches!(
                error.downcast_ref::<ConfigError>(),
                Some(ConfigError::UnsafePath { .. })
            )
        ));
        Ok(())
    }

    #[test]
    fn a_sibling_prefix_directory_is_not_mistaken_for_containment(
    ) -> Result<(), TestError> {
        let root = tempdir()?;
        let evil = root.join(".luminosity-evil");
        fs::create_dir_all(&evil)?;
        fs::write(evil.join("context.md"), "secrets\n")?;
        fs::create_dir_all(root.join(".luminosity/skills"))?;
        std::os::unix::fs::symlink(
            &evil,
            root.join(".luminosity/skills/configure"),
        )?;

        assert!(matches!(
            skill_body(&root, Level::Team),
            Err(error) if matches!(
                error.downcast_ref::<ConfigError>(),
                Some(ConfigError::UnsafePath { .. })
            )
        ));
        Ok(())
    }

    #[test]
    fn a_skill_context_under_a_symlinked_root_is_read() -> Result<(), TestError>
    {
        let base = tempdir()?;
        let real = base.join("real");
        let linked = base.join("linked");
        fs::create_dir_all(&real)?;
        std::os::unix::fs::symlink(&real, &linked)?;
        seed_skill(&real, "context.md", "under a symlinked root\n")?;

        assert_eq!(
            skill_body(&linked, Level::Team)?,
            Some("under a symlinked root\n".to_owned())
        );
        Ok(())
    }

    #[test]
    fn a_symlink_to_a_nonexistent_target_reads_as_none() -> Result<(), TestError>
    {
        let root = tempdir()?;
        fs::create_dir_all(skill_dir(&root))?;
        std::os::unix::fs::symlink(
            root.join("nowhere.md"),
            skill_dir(&root).join("context.md"),
        )?;
        assert!(skill_body(&root, Level::Team)?.is_none());
        Ok(())
    }

    #[test]
    fn the_skill_context_path_nests_under_skills() -> Result<(), TestError> {
        let store = FileConfigStore::rooted_at(tempdir()?);
        assert_eq!(
            store.locate(&configure()?)?.paths,
            [
                ".luminosity/skills/configure/context.md".to_owned(),
                ".luminosity/skills/configure/context.local.md".to_owned(),
            ]
        );
        Ok(())
    }

    #[test]
    fn the_project_context_path_is_the_config_file() -> Result<(), TestError> {
        let store = FileConfigStore::rooted_at(tempdir()?);
        assert_eq!(
            store.locate(&ContextSource::Project)?.paths,
            [
                ".luminosity/config.md".to_owned(),
                ".luminosity/config.local.md".to_owned(),
            ]
        );
        Ok(())
    }

    #[test]
    fn read_body_reports_the_path_it_read() -> Result<(), TestError> {
        let root = tempdir()?;
        seed_skill(&root, "context.local.md", "personal\n")?;
        let read = FileConfigStore::rooted_at(&root)
            .read_body(&configure()?, Level::Personal)?;
        assert_eq!(read.path, ".luminosity/skills/configure/context.local.md");
        Ok(())
    }

    #[test]
    fn locate_reports_the_discovered_project_root() -> Result<(), TestError> {
        let root = tempdir()?;
        assert_eq!(
            FileConfigStore::rooted_at(&root)
                .locate(&ContextSource::Project)?
                .root,
            root.display().to_string()
        );
        Ok(())
    }

    #[test]
    fn discover_roots_at_an_ancestor_luminosity() -> Result<(), TestError> {
        let root = tempdir()?;
        fs::create_dir_all(root.join(".luminosity"))?;
        let nested = root.join("a/b");
        fs::create_dir_all(&nested)?;
        assert_eq!(FileConfigStore::discover(&nested).root, root);
        Ok(())
    }

    #[test]
    fn discover_roots_at_a_git_directory() -> Result<(), TestError> {
        let root = tempdir()?;
        fs::create_dir_all(root.join(".git"))?;
        let nested = root.join("sub");
        fs::create_dir_all(&nested)?;
        assert_eq!(FileConfigStore::discover(&nested).root, root);
        Ok(())
    }

    #[test]
    fn discover_roots_at_a_git_file() -> Result<(), TestError> {
        let root = tempdir()?;
        fs::write(root.join(".git"), "gitdir: /elsewhere\n")?;
        let nested = root.join("sub");
        fs::create_dir_all(&nested)?;
        assert_eq!(FileConfigStore::discover(&nested).root, root);
        Ok(())
    }

    #[test]
    fn discover_with_no_marker_roots_at_the_start_dir() -> Result<(), TestError>
    {
        let start = tempdir()?.join("isolated/leaf");
        fs::create_dir_all(&start)?;
        assert_eq!(FileConfigStore::discover(&start).root, start);
        Ok(())
    }
}
