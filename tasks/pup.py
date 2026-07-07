from invoke import Context, Exit, task

from tasks.shared.paths import WORKSPACE_ROOT
from tasks.shared.rust import PUP_NIGHTLY, pup_mode


@task
def check(context: Context) -> None:
    """Enforce intra-crate module-import rules with cargo-pup (nightly lane).

    Provisioning is guaranteed by the mise `depends` edge on deps:install:pup
    (mirroring how every Python check depends on deps:install:python), so the
    body simply runs the tool.
    """
    with context.cd(str(WORKSPACE_ROOT)):
        result = context.run(f"cargo +{PUP_NIGHTLY} pup", warn=True, pty=False)
    if result.exited != 0:
        if pup_mode() == "warn":
            print(
                "WARNING: cargo-pup reported findings (advisory mode, "
                "LUMINOSITY_PUP_MODE=warn — NOT blocking); see output above"
            )
            return
        raise Exit("cargo-pup: module-import rule violation", code=1)
