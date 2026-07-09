import shlex

from invoke import Context, Exit, task

from tasks.shared import minisign
from tasks.shared.paths import RELEASE_PUBLIC_KEY


@task
def generate(
    context: Context,
    force: bool = False,
) -> None:
    """Generate the password-less release minisign keypair.

    Writes the committed public key and its gitignored sibling secret key.
    Refuses to overwrite an existing public key without `--force`, since
    regenerating invalidates every prior release signature.
    """
    secret_key = RELEASE_PUBLIC_KEY.with_suffix(".key")
    if RELEASE_PUBLIC_KEY.exists() and not force:
        raise Exit(
            f"{RELEASE_PUBLIC_KEY} already exists — regenerating invalidates "
            "every prior release signature. Pass --force to overwrite.",
            code=1,
        )
    RELEASE_PUBLIC_KEY.parent.mkdir(parents=True, exist_ok=True)

    command = [
        minisign.MINISIGN,
        "-G",
        "-W",
        "-f",  # minisign overwrite flag; existence is guarded by --force above
        "-p",
        str(RELEASE_PUBLIC_KEY),
        "-s",
        str(secret_key),
    ]
    context.run(shlex.join(command))

    print(
        "\nGenerated the release keypair:\n"
        f"  public  (commit this):   {RELEASE_PUBLIC_KEY}\n"
        f"  secret  (DO NOT commit): {secret_key}\n\n"
        "Next steps:\n"
        "  1. gh secret set LUMINOSITY_RELEASE_SECRET_KEY < "
        f"{secret_key}\n"
        f"  2. Delete the local secret key: rm {secret_key}\n"
        "  3. Rebuild so the launcher re-embeds the new public key: "
        "mise run build:launcher\n"
    )
