# Fastener Engineering Calculator

A Python fastener/joint engineering calculator based on the original command-line calculation script, plus a revised **EasyGUI v3** interface for interactive fastener selection, joint inputs, preload/torque calculations, and fatigue evaluation.

The repository intentionally contains both versions:

- `fastener_designer.py` — the original source calculator, preserved unchanged for reference and numerical comparison.
- `fastener_designer_easygui_v3.py` — the Python 3.12+ GUI version with explicit fatigue-load semantics, UNC/UNF and grade presets, Goodman/Gerber/ASME criterion selection, and highlighted results.

## Features

### Original calculator

The original script evaluates a planar bolted joint using inch/lbf/psi units and includes:

- fastener grip and thread-length calculations
- bolt tensile-stress area
- bolt stiffness
- compression-frustum member stiffness
- joint stiffness constant, `C`
- resultant bolt/member loads
- preload torque estimate
- proof, overload, and separation safety factors
- fatigue calculations using Goodman, Gerber, and ASME Elliptic expressions

The original file is preserved as supplied, including its original assumptions and source-code behavior. This makes it useful as a baseline when comparing the v3 implementation.

### EasyGUI v3

The v3 interface adds:

- Python 3.12+ compatible syntax
- EasyGUI input workflow
- common UNC/UNF thread presets from #4 through 1 inch
- editable nominal diameter, TPI, bolt-head diameter, and bolt-head height
- separate fastener grade/material presets
- editable proof strength, ultimate tensile strength, and endurance strength
- through-bolt and tapped-hole joint modes
- Goodman, Gerber, and ASME Elliptic fatigue-criterion selection
- explanations of the fatigue criteria and load models
- explicit fatigue-loading definitions to prevent load-range/load-amplitude ambiguity
- source-compatible and nonnegative bolt-stiffness options
- highlighted static and fatigue safety factors in the Results window
- highlighted selected fatigue criterion/result
- detailed intermediate fatigue quantities including load range, mean load, alternating load, preload stress, mean stress, and alternating stress
- text-report export

## Fatigue loading modes

v3 provides four explicit fatigue input interpretations.

### 1. Source-compatible Shigley range (`P_min / P_max`)

This mode is intended for comparison with the original source calculator. It uses

```text
Delta P = P_max - P_min
P_a     = Delta P / 2
sigma_a = C * P_a / A_t
sigma_i = F_i / A_t
sigma_m = sigma_i + sigma_a
```

and evaluates the preloaded-fastener Goodman, Gerber, and ASME Elliptic safety-factor expressions used by the source implementation.

### 2. Repeated load (`0 -> P_max`, Shigley)

For a physical repeated external tensile load from zero to `P_max`,

```text
P_m = P_max / 2
P_a = P_max / 2
```

and the preloaded-fastener Shigley fatigue treatment is applied.

### 3. Minimum / maximum endpoints (general)

For physical cycle endpoints `P_min` and `P_max`,

```text
P_m = (P_max + P_min) / 2
P_a = (P_max - P_min) / 2
```

The resulting mean and alternating bolt stresses are evaluated using the conventional Goodman, Gerber, and ASME mean-stress loci.

### 4. Mean / alternating load (general)

This mode accepts `P_m` and `P_a` directly and reconstructs the physical minimum and maximum loads.

## Fatigue criteria

The GUI allows comparison of all three criteria while identifying the selected design result.

- **Goodman** — linear and generally conservative; useful as a default preliminary-design criterion.
- **Gerber** — parabolic and generally less conservative than Goodman for ductile materials with well-characterized fatigue behavior. A separate proof/yield check should still be maintained.
- **ASME Elliptic** — elliptic interaction between alternating stress and a proof/yield-side limit. In this calculator the proof strength `S_p` is used for the limiting stress in the ASME treatment.

## Installation

### 1. Install Python

Use **Python 3.12 or newer**.

### 2. Create a virtual environment (recommended)

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

The only pip dependency is EasyGUI. The highlighted Results window uses Python's built-in Tkinter GUI toolkit. On some Linux distributions, Tkinter may need to be installed separately through the operating system package manager.

## Running the GUI

```bash
python fastener_designer_easygui_v3.py
```

On Windows, you can also use:

```powershell
py -3.12 fastener_designer_easygui_v3.py
```

## Running the original calculator

```bash
python fastener_designer.py
```

The original script has no GUI. Edit its parameter block directly before running it.

## Repository layout

```text
fastener-engineering-calculator/
├── fastener_designer.py
├── fastener_designer_easygui_v3.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Engineering notes and limitations

- Internal units are inches, lbf, and psi.
- The model is intended for planar bolted-joint calculations and preliminary engineering analysis.
- Thread presets provide common Unified thread geometry and approximate bolt-head geometry for convenience.
- Strength is kept separate from thread geometry because UNC/UNF designation does not define the bolt material or grade.
- The grade presets in the GUI are marked **preliminary**. Verify proof, ultimate, and fatigue properties against the governing fastener standard, manufacturer data, material condition, size range, surface treatment, and service environment before using the results for released hardware.
- The custom/original strength preset intentionally preserves the original script values for comparison, even though the original default `S_p` is greater than the original default `S_ut`.
- The original script is intentionally not silently corrected. For example, its tapped-hole branch references `h` without defining it in the original parameter block, and its final Gerber print statement displays the Goodman variable. The v3 GUI handles those cases separately while retaining a source-compatible calculation mode where appropriate.
- Bolt-head geometry presets are convenient approximations rather than a substitute for the applicable dimensional standard or purchased-fastener drawing.
- Preload torque is highly sensitive to friction assumptions. Use validated nut-factor/friction data for production torque specifications.
- Always check additional failure modes applicable to the real joint, including bearing, thread stripping, shear, combined loading, embedment/relaxation, thermal effects, material yielding, member failure, and environment-specific fatigue effects.

## Reference basis

The original script cites:

> Shigley's Mechanical Engineering Design, 10th edition — Chapter 8 (fasteners and bolted joints).

The source code also contains the reference URL originally supplied with the calculator.

## Version notes

### v3

- added explicit fatigue-load input semantics
- restored a source-compatible fatigue mode for direct comparison with the original calculator
- added an exact repeated-load Shigley mode
- added general min/max and mean/alternating load modes
- added source-compatible vs. nonnegative bolt-stiffness options
- added UNC/UNF thread and preliminary bolt-grade presets
- added Goodman/Gerber/ASME criterion explanations and selection
- highlighted safety factors and selected fatigue result in the Results window
- retained corrected Unified-thread torque handling from the GUI revisions

## License

No license file is included. Add the license you want to apply before publishing the repository if you intend others to copy, modify, or redistribute the code.
