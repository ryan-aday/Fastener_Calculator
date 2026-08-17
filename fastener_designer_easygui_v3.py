"""Fastener Engineering Calculator - EasyGUI v3.

Python: 3.12+
GUI dependency: easygui 0.98.3 (or compatible)

Engineering notes
-----------------
* Internal units are inches, lbf, and psi.
* Unified-thread presets set nominal diameter, TPI, and approximate hex-head
  geometry. Fastener strength remains a separate material/grade selection.
* v3 makes cyclic-load semantics explicit so a load range is never silently
  treated as a load amplitude (or vice versa).
* A source-compatible Shigley mode is retained so the original script's
  fatigue calculations can be reproduced using P_min/P_max as a load range.
* A separate exact repeated-load mode implements the Shigley preloaded-bolt
  equations for an external load cycling from 0 to P_max.
* General min/max and mean/alternating modes use conventional mean-stress
  Goodman, Gerber, and ASME-elliptic loci.
* The results window uses Tkinter (the same GUI toolkit EasyGUI uses) so safety
  factors and the selected fatigue criterion can be visually highlighted.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import atan, cos, inf, isfinite, log, pi, radians, sqrt, tan
from pathlib import Path
from typing import Any

try:
    import easygui as eg
except ImportError as exc:  # pragma: no cover - only happens on user machine
    raise SystemExit(
        "EasyGUI is required. Install it with:  python -m pip install easygui"
    ) from exc


APP_TITLE = "Fastener Engineering Calculator v3"


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

THREAD_PRESETS: dict[str, dict[str, float]] = {
    "Custom / original defaults (1/4-28)": {
        "d": 0.2500,
        "TPI": 28,
        "d_h": 0.4000,
        "bolt_head_h": 0.2000,
    },
    "#4-40 UNC": {"d": 0.1120, "TPI": 40, "d_h": 0.2500, "bolt_head_h": 0.1094},
    "#4-48 UNF": {"d": 0.1120, "TPI": 48, "d_h": 0.2500, "bolt_head_h": 0.1094},
    "#6-32 UNC": {"d": 0.1380, "TPI": 32, "d_h": 0.3125, "bolt_head_h": 0.1250},
    "#6-40 UNF": {"d": 0.1380, "TPI": 40, "d_h": 0.3125, "bolt_head_h": 0.1250},
    "#8-32 UNC": {"d": 0.1640, "TPI": 32, "d_h": 0.3438, "bolt_head_h": 0.1406},
    "#8-36 UNF": {"d": 0.1640, "TPI": 36, "d_h": 0.3438, "bolt_head_h": 0.1406},
    "#10-24 UNC": {"d": 0.1900, "TPI": 24, "d_h": 0.3750, "bolt_head_h": 0.1563},
    "#10-32 UNF": {"d": 0.1900, "TPI": 32, "d_h": 0.3750, "bolt_head_h": 0.1563},
    "1/4-20 UNC": {"d": 0.2500, "TPI": 20, "d_h": 0.4375, "bolt_head_h": 0.1719},
    "1/4-28 UNF": {"d": 0.2500, "TPI": 28, "d_h": 0.4375, "bolt_head_h": 0.1719},
    "5/16-18 UNC": {"d": 0.3125, "TPI": 18, "d_h": 0.5000, "bolt_head_h": 0.2031},
    "5/16-24 UNF": {"d": 0.3125, "TPI": 24, "d_h": 0.5000, "bolt_head_h": 0.2031},
    "3/8-16 UNC": {"d": 0.3750, "TPI": 16, "d_h": 0.5625, "bolt_head_h": 0.2344},
    "3/8-24 UNF": {"d": 0.3750, "TPI": 24, "d_h": 0.5625, "bolt_head_h": 0.2344},
    "7/16-14 UNC": {"d": 0.4375, "TPI": 14, "d_h": 0.6250, "bolt_head_h": 0.2813},
    "7/16-20 UNF": {"d": 0.4375, "TPI": 20, "d_h": 0.6250, "bolt_head_h": 0.2813},
    "1/2-13 UNC": {"d": 0.5000, "TPI": 13, "d_h": 0.7500, "bolt_head_h": 0.3125},
    "1/2-20 UNF": {"d": 0.5000, "TPI": 20, "d_h": 0.7500, "bolt_head_h": 0.3125},
    "9/16-12 UNC": {"d": 0.5625, "TPI": 12, "d_h": 0.8125, "bolt_head_h": 0.3594},
    "9/16-18 UNF": {"d": 0.5625, "TPI": 18, "d_h": 0.8125, "bolt_head_h": 0.3594},
    "5/8-11 UNC": {"d": 0.6250, "TPI": 11, "d_h": 0.9375, "bolt_head_h": 0.3906},
    "5/8-18 UNF": {"d": 0.6250, "TPI": 18, "d_h": 0.9375, "bolt_head_h": 0.3906},
    "3/4-10 UNC": {"d": 0.7500, "TPI": 10, "d_h": 1.1250, "bolt_head_h": 0.4688},
    "3/4-16 UNF": {"d": 0.7500, "TPI": 16, "d_h": 1.1250, "bolt_head_h": 0.4688},
    "7/8-9 UNC": {"d": 0.8750, "TPI": 9, "d_h": 1.3125, "bolt_head_h": 0.5469},
    "7/8-14 UNF": {"d": 0.8750, "TPI": 14, "d_h": 1.3125, "bolt_head_h": 0.5469},
    "1-8 UNC": {"d": 1.0000, "TPI": 8, "d_h": 1.5000, "bolt_head_h": 0.6094},
    "1-12 UNF": {"d": 1.0000, "TPI": 12, "d_h": 1.5000, "bolt_head_h": 0.6094},
}


GRADE_PRESETS: dict[str, dict[str, float]] = {
    "Custom / original strengths": {"S_p": 120_000.0, "S_ut": 58_000.0, "S_e": 23_200.0},
    "SAE J429 Grade 2 (preliminary)": {"S_p": 55_000.0, "S_ut": 74_000.0, "S_e": 29_600.0},
    "SAE J429 Grade 5 (preliminary)": {"S_p": 85_000.0, "S_ut": 120_000.0, "S_e": 48_000.0},
    "SAE J429 Grade 8 (preliminary)": {"S_p": 120_000.0, "S_ut": 150_000.0, "S_e": 60_000.0},
}


CRITERION_INFO: dict[str, str] = {
    "Goodman": (
        "GOODMAN\n"
        "Linear mean-stress criterion using S_e and S_ut. Goodman is normally the "
        "conservative/default choice for preliminary design, uncertain service "
        "loading, or cases where additional fatigue margin is appropriate."
    ),
    "Gerber": (
        "GERBER\n"
        "Parabolic mean-stress criterion using S_e and S_ut. Gerber is less "
        "conservative than Goodman and is most appropriate for ductile materials "
        "with reliable fatigue characterization. Keep a separate proof/yield check."
    ),
    "ASME Elliptic": (
        "ASME ELLIPTIC\n"
        "Elliptic interaction between alternating stress and a proof/yield-side "
        "limit. This calculator uses S_p for that limit, making the criterion useful "
        "when fatigue and permanent-deformation avoidance are both important."
    ),
}


LOAD_MODE_INFO: dict[str, str] = {
    "Source-compatible Shigley range (P_min / P_max)": (
        "SOURCE-COMPATIBLE SHIGLEY RANGE\n"
        "Reproduces the original script's fatigue-load interpretation. The entered "
        "P_min and P_max define only the load range ΔP = P_max - P_min. The model "
        "sets P_a = ΔP/2, sigma_a = C*P_a/A_t, sigma_i = F_i/A_t, and "
        "sigma_m = sigma_i + sigma_a, then applies Shigley Eqs. 8-45 through 8-47. "
        "This mode is provided for one-to-one comparison with the source calculator; "
        "it is not the same as treating P_min and P_max as physical cycle endpoints "
        "when P_min is nonzero."
    ),
    "Repeated load 0 -> P_max (Shigley)": (
        "SHIGLEY REPEATED LOAD\n"
        "Exact repeated external tensile load from 0 to P_max. P_a = P_m = P_max/2. "
        "The preloaded-fastener Shigley Eqs. 8-45 through 8-47 are used."
    ),
    "Minimum / maximum endpoints (general)": (
        "GENERAL MIN/MAX ENDPOINTS\n"
        "Treats P_min and P_max as the actual external tensile-load cycle endpoints. "
        "P_m = (P_max + P_min)/2 and P_a = (P_max - P_min)/2. The conventional "
        "Goodman, Gerber, and ASME mean-stress loci are then evaluated using the "
        "resulting sigma_m and sigma_a."
    ),
    "Mean / alternating load (general)": (
        "GENERAL MEAN / ALTERNATING LOAD\n"
        "Treats P_m and P_a as the directly entered mean and alternating external "
        "loads. The physical endpoints are P_min = P_m - P_a and P_max = P_m + P_a."
    ),
}


STIFFNESS_MODEL_INFO: dict[str, str] = {
    "Source-compatible grip lengths": (
        "SOURCE-COMPATIBLE BOLT STIFFNESS\n"
        "Uses the original script exactly: l_d = L - L_t and l_t = l - l_d. "
        "For short bolts this can produce a negative l_d. It is retained so C and "
        "the original safety factors can be reproduced for comparison."
    ),
    "Nonnegative grip segments (recommended)": (
        "NONNEGATIVE BOLT STIFFNESS\n"
        "Constrains the unthreaded length inside the grip to 0 <= l_d <= l and uses "
        "l_t = l - l_d. This avoids a negative physical shank length but can change "
        "the joint constant C relative to the source script."
    ),
}


@dataclass
class Inputs:
    is_through: bool = True
    thread_name: str = "Custom / original defaults (1/4-28)"
    grade_name: str = "Custom / original strengths"
    criterion: str = "Goodman"

    # v3 defaults to source-compatible modes so existing source-script values
    # reproduce the original fatigue calculation as closely as possible.
    load_mode: str = "Source-compatible Shigley range (P_min / P_max)"
    stiffness_model: str = "Source-compatible grip lengths"

    d: float = 0.25
    TPI: float = 28.0
    d_h: float = 0.4
    bolt_head_h: float = 0.2
    bolt_E: float = 3.0e7

    w1_t: float = 0.0
    w2_t: float = 0.0
    w_E: float = 3.0e7
    nut_t: float = 0.0

    m1_t: float = 0.1
    m1_E: float = 1.0e7
    m2_t: float = 0.25
    m2_E: float = 3.0e7

    N: int = 3
    F_i: float = 50.0
    P_total: float = 100.0

    # Existing source defaults are retained.
    P_min: float = 20.0
    P_max: float = 40.0
    P_mean: float = 30.0
    P_alt: float = 10.0

    f: float = 0.15
    f_c: float = 0.15

    S_p: float = 120_000.0
    S_ut: float = 58_000.0
    S_e: float = 23_200.0

    # Only used for the tapped-hole branch.
    tapped_h: float = 0.25


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------


def _series_stiffness(*stiffnesses: float) -> float:
    """Equivalent stiffness of springs in series, ignoring infinite terms."""
    compliance = 0.0
    for k in stiffnesses:
        if k <= 0:
            raise ValueError("Stiffness must be positive.")
        if isfinite(k):
            compliance += 1.0 / k
    return inf if compliance == 0 else 1.0 / compliance


def frustum_stiffness(E: float, D: float, d: float, t: float, alpha: float) -> float:
    """Member compression-frustum stiffness from the source model."""
    if t <= 0:
        return inf
    if E <= 0 or D <= d or d <= 0:
        raise ValueError("Frustum requires E > 0 and D > d > 0.")

    tan_a = tan(alpha)
    num = pi * E * d * tan_a
    den_1 = (2.0 * t * tan_a + D - d) * (D + d)
    den_2 = (2.0 * t * tan_a + D + d) * (D - d)
    ratio = den_1 / den_2
    if ratio <= 0 or abs(ratio - 1.0) < 1e-14:
        raise ValueError("Invalid compression-frustum geometry.")
    return num / log(ratio)


def _shigley_preloaded_safety_factors(
    sigma_a: float,
    sigma_i: float,
    S_e: float,
    S_ut: float,
    S_p: float,
) -> dict[str, float]:
    """Shigley preloaded-fastener repeated-load Eqs. 8-45 through 8-47."""
    if sigma_a < 0:
        raise ValueError("Alternating stress cannot be negative.")
    if sigma_a == 0:
        return {"Goodman": inf, "Gerber": inf, "ASME Elliptic": inf}

    n_goodman = S_e * (S_ut - sigma_i) / (sigma_a * (S_ut + S_e))

    gerber_radicand = S_ut**2 + 4.0 * S_e * (S_e + sigma_i)
    n_gerber = (
        (S_ut * sqrt(gerber_radicand) - S_ut**2 - 2.0 * sigma_i * S_e)
        / (2.0 * sigma_a * S_e)
        if gerber_radicand >= 0
        else float("nan")
    )

    asme_radicand = S_p**2 + S_e**2 - sigma_i**2
    n_asme = (
        S_e
        * (S_p * sqrt(asme_radicand) - sigma_i * S_e)
        / (sigma_a * (S_p**2 + S_e**2))
        if asme_radicand >= 0
        else float("nan")
    )

    return {
        "Goodman": n_goodman,
        "Gerber": n_gerber,
        "ASME Elliptic": n_asme,
    }


def _general_mean_stress_safety_factors(
    sigma_a: float,
    sigma_m: float,
    S_e: float,
    S_ut: float,
    S_p: float,
) -> dict[str, float]:
    """Conventional radial Goodman, Gerber, and ASME-elliptic safety factors."""
    if sigma_a < 0:
        raise ValueError("Alternating stress cannot be negative.")

    goodman_term = sigma_a / S_e + sigma_m / S_ut
    n_goodman = inf if goodman_term <= 0 else 1.0 / goodman_term

    # Gerber: n*sigma_a/S_e + (n*sigma_m/S_ut)^2 = 1.
    gerber_a = (sigma_m / S_ut) ** 2
    gerber_b = sigma_a / S_e
    if gerber_a > 0:
        disc = gerber_b**2 + 4.0 * gerber_a
        n_gerber = (-gerber_b + sqrt(disc)) / (2.0 * gerber_a)
    elif gerber_b > 0:
        n_gerber = 1.0 / gerber_b
    else:
        n_gerber = inf

    # ASME: (n*sigma_a/S_e)^2 + (n*sigma_m/S_p)^2 = 1.
    asme_term = (sigma_a / S_e) ** 2 + (sigma_m / S_p) ** 2
    n_asme = inf if asme_term <= 0 else 1.0 / sqrt(asme_term)

    return {
        "Goodman": n_goodman,
        "Gerber": n_gerber,
        "ASME Elliptic": n_asme,
    }


def fastener_fatigue(
    C: float,
    A_t: float,
    F_i: float,
    P_min: float,
    P_max: float,
    P_mean: float,
    P_alt: float,
    S_e: float,
    S_ut: float,
    S_p: float,
    criterion: str,
    load_mode: str,
) -> dict[str, Any]:
    """Calculate fatigue stresses using an explicit cyclic-load definition."""
    if A_t <= 0:
        raise ValueError("A_t must be greater than zero.")
    if min(S_e, S_ut, S_p) <= 0:
        raise ValueError("S_e, S_ut, and S_p must all be greater than zero.")
    if not 0.0 <= C <= 1.0:
        raise ValueError("Joint stiffness constant C must lie between 0 and 1.")

    sigma_i = F_i / A_t

    if load_mode == "Source-compatible Shigley range (P_min / P_max)":
        if P_max < P_min:
            raise ValueError("P_max must be greater than or equal to P_min.")

        # This is intentionally the same load-range interpretation as the
        # original source script.
        p_range = P_max - P_min
        p_alt_model = p_range / 2.0
        p_mean_input = (P_max + P_min) / 2.0
        p_mean_model = p_alt_model

        sigma_a = C * p_alt_model / A_t
        sigma_m = sigma_i + sigma_a
        sigma_min = sigma_m - sigma_a  # = sigma_i
        sigma_max = sigma_m + sigma_a
        F_b_min = sigma_min * A_t
        F_b_max = sigma_max * A_t

        factors = _shigley_preloaded_safety_factors(
            sigma_a, sigma_i, S_e, S_ut, S_p
        )
        method = "Shigley Eqs. 8-45 through 8-47 (source-compatible range)"
        effective_p_min = 0.0
        effective_p_max = p_range

    elif load_mode == "Repeated load 0 -> P_max (Shigley)":
        if P_max < 0:
            raise ValueError("P_max must be nonnegative for repeated loading.")

        effective_p_min = 0.0
        effective_p_max = P_max
        p_range = P_max
        p_alt_model = P_max / 2.0
        p_mean_input = P_max / 2.0
        p_mean_model = P_max / 2.0

        sigma_a = C * p_alt_model / A_t
        sigma_m = sigma_i + C * p_mean_model / A_t
        sigma_min = sigma_i
        sigma_max = sigma_i + C * P_max / A_t
        F_b_min = F_i
        F_b_max = F_i + C * P_max

        factors = _shigley_preloaded_safety_factors(
            sigma_a, sigma_i, S_e, S_ut, S_p
        )
        method = "Shigley Eqs. 8-45 through 8-47 (0 -> P_max repeated load)"

    elif load_mode == "Minimum / maximum endpoints (general)":
        if P_max < P_min:
            raise ValueError("P_max must be greater than or equal to P_min.")

        effective_p_min = P_min
        effective_p_max = P_max
        p_range = P_max - P_min
        p_alt_model = p_range / 2.0
        p_mean_input = (P_max + P_min) / 2.0
        p_mean_model = p_mean_input

        F_b_min = F_i + C * P_min
        F_b_max = F_i + C * P_max
        sigma_min = F_b_min / A_t
        sigma_max = F_b_max / A_t
        sigma_a = C * p_alt_model / A_t
        sigma_m = sigma_i + C * p_mean_model / A_t

        factors = _general_mean_stress_safety_factors(
            sigma_a, sigma_m, S_e, S_ut, S_p
        )
        method = "General mean-stress loci from physical P_min/P_max endpoints"

    elif load_mode == "Mean / alternating load (general)":
        if P_alt < 0:
            raise ValueError("P_alt must be nonnegative.")

        effective_p_min = P_mean - P_alt
        effective_p_max = P_mean + P_alt
        p_range = 2.0 * P_alt
        p_alt_model = P_alt
        p_mean_input = P_mean
        p_mean_model = P_mean

        F_b_min = F_i + C * effective_p_min
        F_b_max = F_i + C * effective_p_max
        sigma_min = F_b_min / A_t
        sigma_max = F_b_max / A_t
        sigma_a = C * P_alt / A_t
        sigma_m = sigma_i + C * P_mean / A_t

        factors = _general_mean_stress_safety_factors(
            sigma_a, sigma_m, S_e, S_ut, S_p
        )
        method = "General mean-stress loci from entered P_m and P_a"

    else:
        raise ValueError(f"Unknown load mode: {load_mode}")

    if criterion not in factors:
        raise ValueError("criterion must be Goodman, Gerber, or ASME Elliptic.")

    return {
        "load_mode": load_mode,
        "method": method,
        "criterion": criterion,
        "P_min_effective": effective_p_min,
        "P_max_effective": effective_p_max,
        "P_range": p_range,
        "P_mean_input": p_mean_input,
        "P_mean_model": p_mean_model,
        "P_alt_model": p_alt_model,
        "F_b_min": F_b_min,
        "F_b_max": F_b_max,
        "sigma_i": sigma_i,
        "sigma_min": sigma_min,
        "sigma_max": sigma_max,
        "sigma_range": sigma_max - sigma_min,
        "sigma_a": sigma_a,
        "sigma_m": sigma_m,
        "Goodman": factors["Goodman"],
        "Gerber": factors["Gerber"],
        "ASME Elliptic": factors["ASME Elliptic"],
        "n_f_selected": factors[criterion],
    }


def calculate(inp: Inputs) -> dict[str, Any]:
    """Perform the fastener calculations."""
    if inp.d <= 0 or inp.TPI <= 0:
        raise ValueError("Nominal diameter and TPI must be positive.")
    if inp.d_h <= inp.d:
        raise ValueError("Head/effective bearing diameter must be greater than bolt diameter.")
    if inp.bolt_head_h <= 0:
        raise ValueError("Bolt head height must be positive.")
    if inp.N <= 0:
        raise ValueError("Number of bolts must be at least 1.")
    if inp.m1_t < 0 or inp.m2_t < 0 or inp.w1_t < 0 or inp.w2_t < 0 or inp.nut_t < 0:
        raise ValueError("Thickness values cannot be negative.")
    if inp.m1_t + inp.m2_t + inp.w1_t + inp.w2_t <= 0:
        raise ValueError("Total grip thickness must be positive.")

    warnings: list[str] = []
    if inp.S_p > inp.S_ut:
        warnings.append(
            "Proof strength exceeds ultimate strength. This reproduces the original "
            "custom defaults but is not physically consistent; select a standard grade "
            "or edit the strengths before design release."
        )
    if inp.S_e >= inp.S_ut:
        warnings.append("Endurance strength is unusually high relative to ultimate strength.")

    # Grip & fastener length
    base_grip = inp.w1_t + inp.m1_t + inp.m2_t + inp.w2_t
    if inp.is_through:
        l = base_grip
        L = l + inp.nut_t
    else:
        h = inp.tapped_h
        L = h + 1.5 * inp.d
        l = h + (inp.d / 2.0 if inp.m2_t >= inp.d else inp.m2_t / 2.0)
        warnings.append(
            "Tapped-hole mode follows the source script's approximate effective-length "
            "model. Verify actual thread engagement and member bearing assumptions."
        )

    # Threaded / unthreaded lengths in the grip.
    L_t = 2.0 * inp.d + (0.25 if L <= 6.0 else 0.5)
    source_l_d = L - L_t
    if inp.stiffness_model == "Source-compatible grip lengths":
        l_d = source_l_d
        l_t = l - l_d
        if l_d < 0:
            warnings.append(
                "Source-compatible bolt stiffness produced negative l_d. This matches "
                "the original script algebra but is not a physical negative shank length. "
                "Use 'Nonnegative grip segments' for the constrained interpretation."
            )
    elif inp.stiffness_model == "Nonnegative grip segments (recommended)":
        l_d = min(l, max(0.0, source_l_d))
        l_t = l - l_d
    else:
        raise ValueError(f"Unknown stiffness model: {inp.stiffness_model}")

    A_d = pi * inp.d**2 / 4.0
    A_t = 0.7854 * (inp.d - 0.9743 / inp.TPI) ** 2
    if A_t <= 0:
        raise ValueError("Calculated tensile-stress area is non-positive; check d and TPI.")

    bolt_compliance = l_d / (A_d * inp.bolt_E) + l_t / (A_t * inp.bolt_E)
    if bolt_compliance <= 0:
        raise ValueError(
            "Calculated bolt compliance is non-positive. Switch to the nonnegative grip "
            "model or check the selected geometry."
        )
    k_b = 1.0 / bolt_compliance

    # Member compression geometry
    frustum_alpha = atan((inp.d_h / 2.0) / inp.bolt_head_h)
    frustum_mid_plane = l / 2.0
    frustum_outer_diameter = (
        (inp.m2_t + inp.w2_t)
        + 2.0 * (inp.w1_t + inp.m1_t) * tan(frustum_alpha)
    )

    if inp.w1_t + inp.m1_t < frustum_mid_plane:
        middle_t = inp.m2_t + inp.w2_t - frustum_mid_plane
        middle_E = inp.m2_E
    else:
        middle_t = inp.w1_t + inp.m1_t - frustum_mid_plane
        middle_E = inp.m1_E

    k_1 = frustum_stiffness(
        inp.m1_E, inp.d_h, inp.d, inp.w1_t + inp.m1_t, frustum_alpha
    )
    k_2 = frustum_stiffness(
        inp.m2_E, inp.d_h, inp.d, inp.m2_t + inp.w2_t, frustum_alpha
    )

    try:
        k_mid = frustum_stiffness(middle_E, inp.d_h, inp.d, middle_t, frustum_alpha)
        k_m = _series_stiffness(k_1, k_mid, k_2)
    except (ValueError, ZeroDivisionError):
        k_mid = inf
        k_m = _series_stiffness(k_1, k_2)
        warnings.append(
            "The middle compression-frustum segment was geometrically degenerate; "
            "member stiffness used the two outer segments only."
        )

    # Joint constant and static loading
    P = inp.P_total / inp.N
    C = k_b / (k_b + k_m)
    F_b = C * P + inp.F_i
    F_m = (1.0 - C) * P - inp.F_i

    # Unified 60-degree thread torque model. This keeps the v2 correction that
    # uses thread lead and a 30-degree thread half-angle rather than grip length
    # and the member-compression frustum angle.
    d_minor = inp.d - 1.299038 / inp.TPI
    if d_minor <= 0:
        raise ValueError("Calculated minor diameter is non-positive; check d and TPI.")

    lead = 1.0 / inp.TPI
    tan_lambda = lead / (pi * d_minor)
    thread_half_angle = radians(30.0)
    sec_thread_half_angle = 1.0 / cos(thread_half_angle)

    friction_term = inp.f * sec_thread_half_angle
    torque_denom = 1.0 - inp.f * tan_lambda * sec_thread_half_angle
    if abs(torque_denom) < 1e-12:
        raise ValueError("Thread torque denominator is near zero; check friction inputs.")

    K = (
        (d_minor / (2.0 * inp.d))
        * (tan_lambda + friction_term)
        / torque_denom
        + 0.625 * inp.f_c
    )
    T = K * inp.F_i * inp.d

    # Static tensile checks
    S_b = F_b / A_t
    n_p = (inp.S_p * A_t / F_b) if F_b > 0 else inf
    n_l = ((inp.S_p * A_t - inp.F_i) / (C * P)) if C * P > 0 else inf
    n_0 = (inp.F_i / (P * (1.0 - C))) if P * (1.0 - C) > 0 else inf
    F_p = A_t * inp.S_p

    fatigue = fastener_fatigue(
        C=C,
        A_t=A_t,
        F_i=inp.F_i,
        P_min=inp.P_min,
        P_max=inp.P_max,
        P_mean=inp.P_mean,
        P_alt=inp.P_alt,
        S_e=inp.S_e,
        S_ut=inp.S_ut,
        S_p=inp.S_p,
        criterion=inp.criterion,
        load_mode=inp.load_mode,
    )

    # C-based load sharing only applies while the joint remains closed.
    p_sep = inp.F_i / (1.0 - C) if (1.0 - C) > 0 else inf
    if fatigue["P_max_effective"] >= p_sep:
        warnings.append(
            "The fatigue-cycle maximum external load reaches/exceeds the approximate "
            "joint-separation load F_i/(1-C). The constant-C closed-joint fatigue model "
            "is not valid beyond separation."
        )

    if inp.load_mode == "Source-compatible Shigley range (P_min / P_max)":
        warnings.append(
            "Source-compatible fatigue mode intentionally uses P_min/P_max only to form "
            "ΔP, matching the original script. Select a general endpoint mode if the "
            "nonzero mean external load should contribute to sigma_m."
        )

    return {
        "l": l,
        "L": L,
        "L_t": L_t,
        "source_l_d": source_l_d,
        "l_d": l_d,
        "l_t": l_t,
        "A_d": A_d,
        "A_t": A_t,
        "k_b": k_b,
        "k_1": k_1,
        "k_mid": k_mid,
        "k_2": k_2,
        "k_m": k_m,
        "C": C,
        "P": P,
        "F_b": F_b,
        "F_m": F_m,
        "frustum_alpha_deg": frustum_alpha * 180.0 / pi,
        "frustum_outer_diameter": frustum_outer_diameter,
        "d_minor": d_minor,
        "lead": lead,
        "helix_angle_deg": atan(tan_lambda) * 180.0 / pi,
        "K": K,
        "T": T,
        "S_b": S_b,
        "n_p": n_p,
        "n_l": n_l,
        "n_0": n_0,
        "F_p": F_p,
        "p_sep": p_sep,
        "fatigue": fatigue,
        "selected_nf": fatigue["n_f_selected"],
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# GUI helpers
# ---------------------------------------------------------------------------


def _preselect_index(keys: list[str], current: str) -> int:
    try:
        return keys.index(current)
    except ValueError:
        return 0


def _set_cycle_from_endpoints(inp: Inputs, p_min: float, p_max: float) -> None:
    inp.P_min = p_min
    inp.P_max = p_max
    inp.P_mean = (p_max + p_min) / 2.0
    inp.P_alt = (p_max - p_min) / 2.0


def _current_physical_endpoints(inp: Inputs) -> tuple[float, float]:
    if inp.load_mode == "Mean / alternating load (general)":
        return inp.P_mean - inp.P_alt, inp.P_mean + inp.P_alt
    if inp.load_mode == "Repeated load 0 -> P_max (Shigley)":
        return 0.0, inp.P_max
    return inp.P_min, inp.P_max


def choose_preset(inp: Inputs) -> bool:
    thread_names = list(THREAD_PRESETS)
    selected_thread = eg.choicebox(
        "Choose a Unified thread preset.\n\n"
        "The preset fills nominal diameter, TPI, and approximate hex-head geometry. "
        "All values can be edited on the next screen.",
        APP_TITLE,
        thread_names,
        preselect=_preselect_index(thread_names, inp.thread_name),
    )
    if selected_thread is None:
        return False
    inp.thread_name = str(selected_thread)
    thread = THREAD_PRESETS[inp.thread_name]
    inp.d = thread["d"]
    inp.TPI = thread["TPI"]
    inp.d_h = thread["d_h"]
    inp.bolt_head_h = thread["bolt_head_h"]

    grade_names = list(GRADE_PRESETS)
    selected_grade = eg.choicebox(
        "Choose a fastener strength preset.\n\n"
        "Strength is separate from UNC/UNF geometry. S_e is an editable preliminary "
        "estimate in the standard presets.",
        APP_TITLE,
        grade_names,
        preselect=_preselect_index(grade_names, inp.grade_name),
    )
    if selected_grade is None:
        return False
    inp.grade_name = str(selected_grade)
    grade = GRADE_PRESETS[inp.grade_name]
    inp.S_p = grade["S_p"]
    inp.S_ut = grade["S_ut"]
    inp.S_e = grade["S_e"]

    joint_names = ["Through-bolt joint", "Tapped-hole joint"]
    joint_choice = eg.choicebox(
        "Choose the joint type.",
        APP_TITLE,
        joint_names,
        preselect=0 if inp.is_through else 1,
    )
    if joint_choice is None:
        return False
    inp.is_through = str(joint_choice) == "Through-bolt joint"

    # Preserve the physical cycle when changing how the user wants to enter it.
    old_p_min, old_p_max = _current_physical_endpoints(inp)
    load_modes = list(LOAD_MODE_INFO)
    selected_load_mode = eg.choicebox(
        "Choose how the cyclic external load is defined.\n\n"
        "The first option reproduces the original source-script interpretation.\n"
        "The remaining options make physical cycle endpoints or amplitudes explicit.",
        APP_TITLE,
        load_modes,
        preselect=_preselect_index(load_modes, inp.load_mode),
    )
    if selected_load_mode is None:
        return False
    inp.load_mode = str(selected_load_mode)
    _set_cycle_from_endpoints(inp, old_p_min, old_p_max)
    if inp.load_mode == "Repeated load 0 -> P_max (Shigley)":
        _set_cycle_from_endpoints(inp, 0.0, max(0.0, old_p_max))

    stiffness_modes = list(STIFFNESS_MODEL_INFO)
    selected_stiffness = eg.choicebox(
        "Choose the bolt grip-length interpretation used for stiffness k_b.\n\n"
        "Source-compatible reproduces the original script, including a possible "
        "negative l_d. Nonnegative is the recommended physical constraint.",
        APP_TITLE,
        stiffness_modes,
        preselect=_preselect_index(stiffness_modes, inp.stiffness_model),
    )
    if selected_stiffness is None:
        return False
    inp.stiffness_model = str(selected_stiffness)

    criterion_names = list(CRITERION_INFO)
    selected_criterion = eg.choicebox(
        "Choose the fatigue criterion.\n\n"
        "Goodman: conservative/default.\n"
        "Gerber: less conservative for well-characterized ductile materials.\n"
        "ASME Elliptic: emphasizes proof/yield interaction.",
        APP_TITLE,
        criterion_names,
        preselect=_preselect_index(criterion_names, inp.criterion),
    )
    if selected_criterion is None:
        return False
    inp.criterion = str(selected_criterion)

    show_explanation = eg.ynbox(
        f"Load definition: {inp.load_mode}\n"
        f"Stiffness model: {inp.stiffness_model}\n"
        f"Criterion: {inp.criterion}\n\n"
        "Show model guidance before entering values?",
        APP_TITLE,
        choices=("Show guidance", "Continue"),
        default_choice="Continue",
        cancel_choice="Continue",
    )
    if show_explanation:
        eg.msgbox(
            LOAD_MODE_INFO[inp.load_mode]
            + "\n\n"
            + STIFFNESS_MODEL_INFO[inp.stiffness_model]
            + "\n\n"
            + CRITERION_INFO[inp.criterion],
            APP_TITLE,
        )

    return True


def edit_numeric_inputs(inp: Inputs) -> bool:
    base_fields = [
        "Nominal diameter d [in]",
        "Threads per inch TPI [1/in]",
        "Head / effective bearing diameter d_h [in]",
        "Bolt head height [in]",
        "Bolt elastic modulus E_b [psi]",
        "Washer 1 thickness [in]",
        "Washer 2 thickness [in]",
        "Washer elastic modulus E_w [psi]",
        "Nut thickness [in]",
        "Material 1 thickness [in]",
        "Material 1 elastic modulus [psi]",
        "Material 2 thickness [in]",
        "Material 2 elastic modulus [psi]",
        "Number of bolts N",
        "Preload F_i [lbf]",
        "Total joint tensile load P_total [lbf]",
    ]
    base_values = [
        inp.d,
        inp.TPI,
        inp.d_h,
        inp.bolt_head_h,
        inp.bolt_E,
        inp.w1_t,
        inp.w2_t,
        inp.w_E,
        inp.nut_t,
        inp.m1_t,
        inp.m1_E,
        inp.m2_t,
        inp.m2_E,
        inp.N,
        inp.F_i,
        inp.P_total,
    ]

    if inp.load_mode in {
        "Source-compatible Shigley range (P_min / P_max)",
        "Minimum / maximum endpoints (general)",
    }:
        cyclic_fields = [
            "Minimum cyclic load per bolt P_min [lbf]",
            "Maximum cyclic load per bolt P_max [lbf]",
        ]
        cyclic_values = [inp.P_min, inp.P_max]
    elif inp.load_mode == "Repeated load 0 -> P_max (Shigley)":
        cyclic_fields = ["Repeated-load maximum per bolt P_max [lbf] (cycle is 0 -> P_max)"]
        cyclic_values = [inp.P_max]
    else:
        cyclic_fields = [
            "Mean cyclic load per bolt P_m [lbf]",
            "Alternating cyclic load amplitude per bolt P_a [lbf]",
        ]
        cyclic_values = [inp.P_mean, inp.P_alt]

    tail_fields = [
        "Thread friction coefficient f",
        "Bearing/Coulomb friction coefficient f_c",
        "Minimum proof strength S_p [psi]",
        "Ultimate tensile strength S_ut [psi]",
        "Endurance strength S_e [psi]",
        "Free grip thickness above tapped member h [in] (ignored for through-bolt)",
    ]
    tail_values = [inp.f, inp.f_c, inp.S_p, inp.S_ut, inp.S_e, inp.tapped_h]

    fields = base_fields + cyclic_fields + tail_fields
    values = base_values + cyclic_values + tail_values

    while True:
        entered = eg.multenterbox(
            "Review/edit the parameters. Existing source values remain the defaults.\n\n"
            f"Cyclic-load definition: {inp.load_mode}\n"
            f"Bolt stiffness model: {inp.stiffness_model}\n\n"
            "Units: inches, lbf, psi.",
            APP_TITLE,
            fields,
            [f"{v:g}" for v in values],
        )
        if entered is None:
            return False

        errors: list[str] = []
        parsed: list[float] = []
        for field, raw in zip(fields, entered):
            try:
                parsed.append(float(raw))
            except (TypeError, ValueError):
                errors.append(f"{field}: enter a numeric value")
                parsed.append(0.0)

        if errors:
            eg.msgbox("Please correct:\n\n" + "\n".join(errors), APP_TITLE)
            values = entered
            continue

        if parsed[13] < 1 or abs(parsed[13] - round(parsed[13])) > 1e-9:
            errors.append("Number of bolts N must be a positive integer.")
        if parsed[1] <= 0:
            errors.append("TPI must be positive.")
        if parsed[0] <= 0:
            errors.append("Nominal diameter must be positive.")

        cyclic_start = len(base_fields)
        if inp.load_mode in {
            "Source-compatible Shigley range (P_min / P_max)",
            "Minimum / maximum endpoints (general)",
        }:
            pmin = parsed[cyclic_start]
            pmax = parsed[cyclic_start + 1]
            if pmax < pmin:
                errors.append("P_max must be greater than or equal to P_min.")
        elif inp.load_mode == "Repeated load 0 -> P_max (Shigley)":
            if parsed[cyclic_start] < 0:
                errors.append("Repeated-load P_max must be nonnegative.")
        else:
            if parsed[cyclic_start + 1] < 0:
                errors.append("Alternating load amplitude P_a must be nonnegative.")

        if errors:
            eg.msgbox("Please correct:\n\n" + "\n".join(errors), APP_TITLE)
            values = entered
            continue

        # Assign the fixed fields.
        (
            inp.d,
            inp.TPI,
            inp.d_h,
            inp.bolt_head_h,
            inp.bolt_E,
            inp.w1_t,
            inp.w2_t,
            inp.w_E,
            inp.nut_t,
            inp.m1_t,
            inp.m1_E,
            inp.m2_t,
            inp.m2_E,
            n_float,
            inp.F_i,
            inp.P_total,
        ) = parsed[: len(base_fields)]
        inp.N = int(round(n_float))

        idx = len(base_fields)
        if inp.load_mode in {
            "Source-compatible Shigley range (P_min / P_max)",
            "Minimum / maximum endpoints (general)",
        }:
            _set_cycle_from_endpoints(inp, parsed[idx], parsed[idx + 1])
            idx += 2
        elif inp.load_mode == "Repeated load 0 -> P_max (Shigley)":
            _set_cycle_from_endpoints(inp, 0.0, parsed[idx])
            idx += 1
        else:
            inp.P_mean = parsed[idx]
            inp.P_alt = parsed[idx + 1]
            _set_cycle_from_endpoints(
                inp,
                inp.P_mean - inp.P_alt,
                inp.P_mean + inp.P_alt,
            )
            # _set_cycle_from_endpoints recalculates P_mean/P_alt consistently.
            idx += 2

        (
            inp.f,
            inp.f_c,
            inp.S_p,
            inp.S_ut,
            inp.S_e,
            inp.tapped_h,
        ) = parsed[idx : idx + len(tail_fields)]
        return True


def _fmt(value: float, unit: str = "", digits: int = 5) -> str:
    if value == inf:
        return f"infinite {unit}".strip()
    if value != value:  # NaN
        return f"NaN {unit}".strip()
    if abs(value) >= 1e5 or (0 < abs(value) < 1e-3):
        out = f"{value:.5e}"
    else:
        out = f"{value:.{digits}f}"
    return f"{out} {unit}".rstrip()


def make_report(inp: Inputs, r: dict[str, Any]) -> str:
    fatigue = r["fatigue"]
    warning_text = "None"
    if r["warnings"]:
        warning_text = "\n".join(f"- {w}" for w in r["warnings"])

    return f"""FASTENER ENGINEERING CALCULATOR v3
===================================

Selections
----------
Thread preset:          {inp.thread_name}
Strength preset:        {inp.grade_name}
Joint type:             {'Through-bolt' if inp.is_through else 'Tapped-hole'}
Cyclic-load definition: {inp.load_mode}
Bolt stiffness model:   {inp.stiffness_model}
Fatigue criterion:      {inp.criterion}
Fatigue method:         {fatigue['method']}

Input summary
-------------
d                      = {_fmt(inp.d, 'in')}
TPI                    = {_fmt(inp.TPI, '1/in')}
d_h                    = {_fmt(inp.d_h, 'in')}
head height            = {_fmt(inp.bolt_head_h, 'in')}
E_b                    = {_fmt(inp.bolt_E, 'psi')}
N                      = {inp.N}
F_i                    = {_fmt(inp.F_i, 'lbf')}
P_total                = {_fmt(inp.P_total, 'lbf')}
Entered P_min / P_max  = {_fmt(inp.P_min, 'lbf')} / {_fmt(inp.P_max, 'lbf')}
Entered P_m / P_a      = {_fmt(inp.P_mean, 'lbf')} / {_fmt(inp.P_alt, 'lbf')}
S_p                    = {_fmt(inp.S_p, 'psi')}
S_ut                   = {_fmt(inp.S_ut, 'psi')}
S_e                    = {_fmt(inp.S_e, 'psi')}

Geometry and stiffness
----------------------
Grip length l          = {_fmt(r['l'], 'in')}
Fastener length L      = {_fmt(r['L'], 'in')}
Thread length L_t      = {_fmt(r['L_t'], 'in')}
Source l_d = L-L_t     = {_fmt(r['source_l_d'], 'in')}
Used unthreaded l_d    = {_fmt(r['l_d'], 'in')}
Used threaded l_t      = {_fmt(r['l_t'], 'in')}
Shank area A_d         = {_fmt(r['A_d'], 'in^2')}
Tensile area A_t       = {_fmt(r['A_t'], 'in^2')}
Minor diameter         = {_fmt(r['d_minor'], 'in')}
Bolt stiffness k_b     = {_fmt(r['k_b'], 'lbf/in')}
Member stiffness k_m   = {_fmt(r['k_m'], 'lbf/in')}
Joint constant C       = {_fmt(r['C'])}
Frustum angle          = {_fmt(r['frustum_alpha_deg'], 'deg')}

Static loading / safety
-----------------------
Load per bolt P        = {_fmt(r['P'], 'lbf')}
Resultant bolt load    = {_fmt(r['F_b'], 'lbf')}
Resultant member load  = {_fmt(r['F_m'], 'lbf')}
Bolt tensile stress    = {_fmt(r['S_b'], 'psi')}
Proof force F_p        = {_fmt(r['F_p'], 'lbf')}
Proof safety factor    = {_fmt(r['n_p'])}
Load factor n_l        = {_fmt(r['n_l'])}
Separation factor n_0  = {_fmt(r['n_0'])}
Separation load/bolt   = {_fmt(r['p_sep'], 'lbf')}

Preload torque
--------------
Thread lead            = {_fmt(r['lead'], 'in/rev')}
Helix angle            = {_fmt(r['helix_angle_deg'], 'deg')}
Torque coefficient K   = {_fmt(r['K'])}
Preload torque T       = {_fmt(r['T'], 'lbf-in')}

Cyclic-load interpretation
--------------------------
Effective P_min        = {_fmt(fatigue['P_min_effective'], 'lbf')}
Effective P_max        = {_fmt(fatigue['P_max_effective'], 'lbf')}
External load range ΔP = {_fmt(fatigue['P_range'], 'lbf')}
Input arithmetic P_m   = {_fmt(fatigue['P_mean_input'], 'lbf')}
Model mean load P_m    = {_fmt(fatigue['P_mean_model'], 'lbf')}
Model alt. load P_a    = {_fmt(fatigue['P_alt_model'], 'lbf')}

Fatigue stresses
----------------
Bolt force min         = {_fmt(fatigue['F_b_min'], 'lbf')}
Bolt force max         = {_fmt(fatigue['F_b_max'], 'lbf')}
Stress min             = {_fmt(fatigue['sigma_min'], 'psi')}
Stress max             = {_fmt(fatigue['sigma_max'], 'psi')}
Bolt stress range Δσ   = {_fmt(fatigue['sigma_range'], 'psi')}
Alternating stress σ_a = {_fmt(fatigue['sigma_a'], 'psi')}
Mean stress σ_m        = {_fmt(fatigue['sigma_m'], 'psi')}
Preload stress σ_i     = {_fmt(fatigue['sigma_i'], 'psi')}

SAFETY FACTORS
--------------
Static proof n_p       = {_fmt(r['n_p'])}
Static load n_l        = {_fmt(r['n_l'])}
Joint separation n_0   = {_fmt(r['n_0'])}
Goodman fatigue n_f    = {_fmt(fatigue['Goodman'])}
Gerber fatigue n_f     = {_fmt(fatigue['Gerber'])}
ASME Elliptic n_f      = {_fmt(fatigue['ASME Elliptic'])}

>>> SELECTED FATIGUE CRITERION: {inp.criterion}
>>> SELECTED FATIGUE SAFETY FACTOR n_f = {_fmt(r['selected_nf'])}

Load-model guidance
-------------------
{LOAD_MODE_INFO[inp.load_mode]}

Stiffness-model guidance
------------------------
{STIFFNESS_MODEL_INFO[inp.stiffness_model]}

Criterion guidance
------------------
{CRITERION_INFO[inp.criterion]}

Warnings / engineering checks
-----------------------------
{warning_text}

Notes
-----
1. UNC/UNF presets define geometry, not material strength.
2. S_e in the standard grade presets is a preliminary 0.40*S_ut estimate and
   should be replaced by a fatigue strength appropriate to thread manufacture,
   size, surface condition, temperature, reliability, and required life.
3. Head geometry presets are approximate and editable. Use the actual fastener
   standard or manufacturer drawing for final bearing/compression calculations.
4. Source-compatible Shigley range mode is intentionally retained for direct
   comparison with the original source script's P_min/P_max fatigue block.
5. Repeated 0->P_max mode uses Shigley Eqs. 8-45 through 8-47 with an explicit
   repeated load. General modes use conventional mean-stress loci.
6. The C-based fatigue model assumes the joint remains closed. If the cycle
   reaches separation, the post-separation load sharing must be modeled separately.
7. This remains a preliminary planar-joint calculator; validate final hardware
   against the governing fastener, joint, fatigue, and safety requirements.
"""


def _sf_tag(value: float, selected: bool = False) -> str:
    """Choose a visual tag for a safety factor in the Tk results window."""
    if value != value or value < 1.0:
        return "selected_danger" if selected else "danger"
    return "selected" if selected else "safety"


def show_results_window(inp: Inputs, r: dict[str, Any], report: str) -> None:
    """Display a highlighted results box using Tkinter's tagged Text widget.

    EasyGUI's codebox is intentionally plain text and cannot highlight individual
    lines. EasyGUI itself is Tkinter-based, so this small results window keeps the
    overall interface lightweight while allowing the requested emphasis.
    """
    try:
        import tkinter as tk
        import tkinter.font as tkfont
        from tkinter.scrolledtext import ScrolledText

        root = tk.Tk()
        root.title(f"{APP_TITLE} - Results")
        root.geometry("980x760")
        root.minsize(760, 560)

        fixed = tkfont.nametofont("TkFixedFont").copy()
        fixed.configure(size=max(9, int(fixed.cget("size"))))
        bold = fixed.copy()
        bold.configure(weight="bold")
        selected_font = fixed.copy()
        selected_font.configure(weight="bold", size=max(10, int(fixed.cget("size")) + 1))

        text = ScrolledText(root, wrap="none", font=fixed, padx=12, pady=12)
        text.pack(fill="both", expand=True, padx=10, pady=(10, 6))

        # Tag colors are intentionally restrained and readable on a standard
        # light Tk theme. The selected criterion receives the strongest emphasis.
        text.tag_configure("heading", font=bold)
        text.tag_configure("safety", font=bold, background="#edf4ff")
        text.tag_configure("selected", font=selected_font, background="#fff0a8")
        text.tag_configure("danger", font=bold, background="#ffd9d9", foreground="#7a0000")
        text.tag_configure(
            "selected_danger",
            font=selected_font,
            background="#ffbcbc",
            foreground="#700000",
        )
        text.tag_configure("warning", foreground="#8a4b00")

        fatigue = r["fatigue"]

        text.insert("end", "SELECTED FATIGUE RESULT\n", "heading")
        selected_line = (
            f"{inp.criterion:<18} n_f = {_fmt(r['selected_nf'])}\n\n"
        )
        text.insert(
            "end",
            selected_line,
            _sf_tag(r["selected_nf"], selected=True),
        )

        text.insert("end", "SAFETY FACTOR SUMMARY\n", "heading")
        summary = [
            ("Static proof n_p", r["n_p"], False),
            ("Static load n_l", r["n_l"], False),
            ("Joint separation n_0", r["n_0"], False),
            ("Goodman fatigue n_f", fatigue["Goodman"], inp.criterion == "Goodman"),
            ("Gerber fatigue n_f", fatigue["Gerber"], inp.criterion == "Gerber"),
            (
                "ASME Elliptic n_f",
                fatigue["ASME Elliptic"],
                inp.criterion == "ASME Elliptic",
            ),
        ]
        for label, value, selected in summary:
            text.insert(
                "end",
                f"{label:<26} = {_fmt(value)}\n",
                _sf_tag(value, selected=selected),
            )

        text.insert("end", "\nFULL CALCULATION REPORT\n", "heading")
        text.insert("end", report)

        if r["warnings"]:
            text.insert("end", "\n\nWarnings are present; review the Warnings section above.\n", "warning")

        text.configure(state="disabled")

        close_button = tk.Button(root, text="Close Results", command=root.destroy, width=18)
        close_button.pack(pady=(0, 10))

        root.mainloop()

    except Exception:
        # Safe fallback if a local Tk theme/window-manager issue occurs.
        eg.codebox("Calculation results", APP_TITLE, report)


def save_report(report: str) -> None:
    path = eg.filesavebox(
        "Save calculation report",
        APP_TITLE,
        default="fastener_calculation_v3.txt",
        filetypes=["*.txt"],
    )
    if not path:
        return
    out = Path(path)
    if out.suffix.lower() != ".txt":
        out = out.with_suffix(".txt")
    out.write_text(report, encoding="utf-8")
    eg.msgbox(f"Saved:\n{out}", APP_TITLE)


def run_gui() -> None:
    inp = Inputs()

    eg.msgbox(
        "Fastener Engineering Calculator v3\n\n"
        "v3 makes cyclic-load input semantics explicit and restores source-compatible "
        "modes for one-to-one comparison with the original calculator. Safety factors "
        "and the selected fatigue criterion are highlighted in the Results window.\n\n"
        "The original numeric values remain loaded as defaults.",
        APP_TITLE,
    )

    while True:
        if not choose_preset(inp):
            return
        if not edit_numeric_inputs(inp):
            return

        try:
            results = calculate(inp)
        except Exception:
            eg.exceptionbox(
                "The calculation failed. Review the inputs and try again.",
                APP_TITLE,
            )
            action = eg.buttonbox(
                "What would you like to do?",
                APP_TITLE,
                choices=("Edit values", "Start over", "Exit"),
                default_choice="Edit values",
                cancel_choice="Exit",
            )
            if action == "Exit" or action is None:
                return
            if action == "Start over":
                inp = Inputs()
            continue

        report = make_report(inp, results)
        show_results_window(inp, results, report)

        action = eg.buttonbox(
            "Calculation complete.",
            APP_TITLE,
            choices=("Edit / rerun", "Save report", "New calculation", "Exit"),
            default_choice="Edit / rerun",
            cancel_choice="Exit",
        )
        if action == "Save report":
            save_report(report)
            continue
        if action == "Edit / rerun":
            continue
        if action == "New calculation":
            inp = Inputs()
            continue
        return


if __name__ == "__main__":
    run_gui()
