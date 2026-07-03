import shlex

from invoke import Context, Exit, task

from tasks.shared import minisign
from tasks.shared.paths import RELEASE_PUBLIC_KEY


@task
def generate(
    context: Context,
    force: bool = False,
    no_password: bool = False,
) -> None:
    """Generate the release minisign keypair.

    Writes the PUBLIC key to `keys/luminosity-release.pub` (committed — the
    launcher embeds it via `cli/launcher/build.rs` and the bootstrap ships it)
    and the SECRET key to the sibling `keys/luminosity-release.key` (gitignored
    by the `*.key` rule). After generating: store the secret key's contents in
    the GitHub `MINISIGN_SECRET_KEY` secret (and its passphrase in
    `MINISIGN_KEY_PASSWORD`), then delete the local secret file.

    Regenerating invalidates every prior release signature, so it refuses to
    overwrite an existing public key without `--force`. Prompts for a passphrase
    interactively unless `--no-password` is given (an unencrypted key).
    """
    # Sibling of the public key, gitignored by the `*.key` rule.
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
        "-f",  # existence is guarded above; -f lets --force actually overwrite
        "-p",
        str(RELEASE_PUBLIC_KEY),
        "-s",
        str(secret_key),
    ]
    if no_password:
        command.append("-W")
    # pty=True so the interactive passphrase prompt works.
    context.run(shlex.join(command), pty=True)

    print(
        "\nGenerated the release keypair:\n"
        f"  public  (commit this):   {RELEASE_PUBLIC_KEY}\n"
        f"  secret  (DO NOT commit): {secret_key}\n\n"
        "Next steps:\n"
        f"  1. Store the contents of {secret_key} in the GitHub "
        "`MINISIGN_SECRET_KEY` secret\n"
        "     (and its passphrase in `MINISIGN_KEY_PASSWORD`).\n"
        f"  2. Delete the local secret key: rm {secret_key}\n"
        "  3. Rebuild so the launcher re-embeds the new public key: "
        "mise run build:launcher\n"
    )
