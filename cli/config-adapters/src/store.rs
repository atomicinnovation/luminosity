//! The filesystem store: it roots the two config files at a discovered project
//! directory and implements the core's read/write ports over `std::fs`.

use std::fs;
use std::io::ErrorKind;
use std::path::{Path, PathBuf};
use std::process;
use std::sync::atomic::{AtomicU64, Ordering};

use config::{
    ConfigError, Level, Node, ReadConfigBody, ReadConfigLevel, WriteConfigLevel,
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

    fn level_path(&self, level: Level) -> PathBuf {
        self.config_dir().join(level.file_name())
    }

    fn read_raw(&self, level: Level) -> Result<Option<Split>, ConfigError> {
        let path = self.level_path(level);
        let content = match fs::read_to_string(&path) {
            Ok(content) => content,
            Err(error) if error.kind() == ErrorKind::NotFound => {
                return Ok(None)
            }
            Err(error) => return Err(io_error(&path, &error)),
        };
        let split = frontmatter::split(&content).map_err(|detail| {
            ConfigError::MalformedFrontmatter {
                path: display(&path),
                detail,
            }
        })?;
        Ok(Some(split))
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
        let Some(split) = self.read_raw(level)? else {
            return Ok(None);
        };
        let node = document::parse_frontmatter(&split.frontmatter).map_err(
            |detail| ConfigError::MalformedFrontmatter {
                path: display(&self.level_path(level)),
                detail,
            },
        )?;
        Ok(Some(node))
    }
}

impl ReadConfigBody for FileConfigStore {
    fn read_body(&self, level: Level) -> Result<Option<String>, ConfigError> {
        Ok(self.read_raw(level)?.map(|split| split.body))
    }
}

impl WriteConfigLevel for FileConfigStore {
    fn write(&self, level: Level, document: &Node) -> Result<(), ConfigError> {
        let path = self.level_path(level);
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

#[cfg(test)]
mod tests {
    use std::fs;
    use std::path::{Path, PathBuf};
    use std::sync::atomic::{AtomicU64, Ordering};

    use config::{
        ConfigAccess, ConfigError, ConfigService, Key, Level, Node,
        ReadConfigBody, ReadConfigLevel, Scalar, WriteConfigLevel,
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
        let store = FileConfigStore::rooted_at(&root);
        assert_eq!(
            store.read_body(Level::Team)?,
            Some("\n  body line\n\n".to_owned())
        );
        Ok(())
    }

    #[test]
    fn an_absent_file_reads_no_body() -> Result<(), TestError> {
        let store = FileConfigStore::rooted_at(tempdir()?);
        assert!(store.read_body(Level::Team)?.is_none());
        Ok(())
    }

    #[test]
    fn a_body_only_file_returns_the_whole_content() -> Result<(), TestError> {
        let root = tempdir()?;
        seed(&root, "config.md", "no frontmatter here\n")?;
        let store = FileConfigStore::rooted_at(&root);
        assert_eq!(
            store.read_body(Level::Team)?,
            Some("no frontmatter here\n".to_owned())
        );
        Ok(())
    }

    #[test]
    fn read_body_fails_loud_on_malformed_frontmatter() -> Result<(), TestError>
    {
        let root = tempdir()?;
        seed(&root, "config.md", "---\nkey: value\n")?;
        let store = FileConfigStore::rooted_at(&root);
        assert!(matches!(
            store.read_body(Level::Team),
            Err(ConfigError::MalformedFrontmatter { path, .. })
                if path.contains("config.md")
        ));
        Ok(())
    }

    #[test]
    fn read_and_read_body_share_one_raw_read() -> Result<(), TestError> {
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
            store.read_body(Level::Team)?,
            Some("body text\n".to_owned())
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
