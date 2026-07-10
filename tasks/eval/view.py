from invoke import Context, task

from tasks.shared.eval.locations import viewer_log_dir


@task(
    help={
        "skill": "Serve only this skill's logs (default: every skill)",
        "host": "Interface to bind (default 127.0.0.1)",
        "port": "Port to serve on (default 7575)",
    }
)
def view(
    context: Context,
    skill: str | None = None,
    host: str = "127.0.0.1",
    port: int = 7575,
) -> None:
    """Open the Inspect log viewer over the committed skill-eval logs."""
    from inspect_ai import view as open_viewer  # noqa: PLC0415  (heavy; lazy)

    open_viewer(
        log_dir=str(viewer_log_dir(skill)),
        recursive=True,
        host=host,
        port=port,
    )
