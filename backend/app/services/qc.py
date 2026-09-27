"""Quality-control helpers: Westgard rule evaluation (pure logic)."""
from typing import List


def evaluate_westgard(values: List[float], mean: float, sd: float) -> List[str]:
    """Evaluate Westgard rules for the LATEST point given the history list.

    ``values`` is chronological with the latest point last. Returns the list
    of violation codes triggered by that latest point:

    - "1_2s": |latest - mean| > 2*sd (warning rule; still recorded)
    - "1_3s": |latest - mean| > 3*sd (reject)
    - "2_2s": last 2 consecutive both > mean+2sd or both < mean-2sd
    - "R_4s": one of last 2 > mean+2sd and the other < mean-2sd
    - "4_1s": last 4 consecutive all > mean+1sd or all < mean-1sd
    - "10_x": last 10 consecutive all > mean or all < mean

    Requires sd > 0 and enough history for each multi-point rule; returns
    [] when the inputs are unusable.
    """
    violations: List[str] = []
    if not values or sd is None or sd <= 0:
        return violations
    nums = []
    for v in values:
        try:
            nums.append(float(v))
        except (TypeError, ValueError):
            return violations
    latest = nums[-1]

    if abs(latest - mean) > 2 * sd:
        violations.append("1_2s")
    if abs(latest - mean) > 3 * sd:
        violations.append("1_3s")

    if len(nums) >= 2:
        last2 = nums[-2:]
        if all(v > mean + 2 * sd for v in last2) or all(v < mean - 2 * sd for v in last2):
            violations.append("2_2s")
        hi, lo = mean + 2 * sd, mean - 2 * sd
        if (last2[0] > hi and last2[1] < lo) or (last2[0] < lo and last2[1] > hi):
            violations.append("R_4s")

    if len(nums) >= 4:
        last4 = nums[-4:]
        if all(v > mean + 1 * sd for v in last4) or all(v < mean - 1 * sd for v in last4):
            violations.append("4_1s")

    if len(nums) >= 10:
        last10 = nums[-10:]
        if all(v > mean for v in last10) or all(v < mean for v in last10):
            violations.append("10_x")

    return violations
