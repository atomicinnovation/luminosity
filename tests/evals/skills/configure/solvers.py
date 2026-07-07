from pathlib import Path

from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import sandbox

from tests.evals.skills.configure.environment import WORKDIR

_FIXTURES = Path(__file__).parent / "fixtures"


@solver
def seed_fixtures() -> Solver:
    """Reset the .git boundary + .luminosity fixture in the sandbox per epoch.

    Removes the whole .luminosity subtree first, then re-seeds, so a prior
    epoch's agent-written config.local.md cannot bleed forward (a plain
    overwrite would leave it behind — it is not part of a team-only seed).
    Writes into the sandbox filesystem, not host-side, since the agent runs in
    the container.
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        source = _FIXTURES / state.metadata["fixture"] / ".luminosity"
        box = sandbox()
        await box.exec(["rm", "-rf", f"{WORKDIR}/.luminosity"])
        await box.exec(
            ["mkdir", "-p", f"{WORKDIR}/.git", f"{WORKDIR}/.luminosity"]
        )
        for path in sorted(source.glob("*")):
            await box.write_file(
                f"{WORKDIR}/.luminosity/{path.name}", path.read_text()
            )
        return state

    return solve
