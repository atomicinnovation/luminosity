"""Authoritative string identifiers shared across the eval tier.

The `tasks/` gate cannot import the (deliberately non-packaged) `tests/` tree,
so it references these by literal; a unit test asserts the two agree, turning a
rename into a fast test failure rather than a live-run failure.
"""

ARM_WITH_SKILL = "configure_with_skill"
ARM_BASELINE = "configure_baseline"
ACCURACY_METRIC = "accuracy"
EPOCHS = 3
# inspect-ai names the pass_k reducer `pass_k_<k>` (verified against 0.3.244);
# with epochs == k it is exactly pass^k — 1.0 iff all k trials pass.
PASS_K_REDUCER = f"pass_k_{EPOCHS}"
SKILL_NAME = "configure"
