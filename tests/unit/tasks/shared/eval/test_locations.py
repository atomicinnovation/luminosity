from tasks.shared.eval.locations import (
    EVALS_SKILLS_DIR,
    results_dir,
    viewer_log_dir,
)


class TestResultsDir:
    def test_points_at_the_skills_results_subdirectory(self):
        assert results_dir("configure") == (
            EVALS_SKILLS_DIR / "configure" / "results"
        )


class TestViewerLogDir:
    def test_serves_a_single_skill_when_named(self):
        assert viewer_log_dir("configure") == results_dir("configure")

    def test_serves_every_skill_when_unnamed(self):
        assert viewer_log_dir(None) == EVALS_SKILLS_DIR
