"""
NASA Battery Dataset Extractor
================================
Converts .mat files (B0005, B0006, B0007, B0018, ...) into a clean per-cycle CSV:

    cycle | discharge_capacity | avg_voltage | end_voltage | discharge_time
          | cv_charge_time | Re | Rct | SOH | RUL

Usage:
    python extract_nasa_battery.py B0005.mat B0006.mat
    python extract_nasa_battery.py *.mat --eol 1.4 --out nasa_features.csv

How each feature is extracted
-------------------------------
discharge_capacity  : Capacity field directly from discharge cycle (Ah)
avg_voltage         : Mean of Voltage_measured array during discharge
end_voltage         : Last value of Voltage_measured in discharge
discharge_time      : Last value of Time array in discharge (seconds)
cv_charge_time      : Duration of CV phase in preceding charge cycle (s)
                      CV phase starts when Voltage_measured >= 4.18 V
Re                  : Electrolyte resistance from nearest impedance cycle (Ω)
Rct                 : Charge transfer resistance from nearest impedance cycle (Ω)
SOH                 : discharge_capacity / first_cycle_capacity  (0–1)
RUL                 : cycles remaining until EOL threshold is crossed
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.io


# ── constants ────────────────────────────────────────────────────────────────
EOL_AH_DEFAULT   = 1.4      # NASA standard: 70% of 2 Ah nominal
CV_VOLTAGE_THRESH = 4.18    # Voltage_measured threshold marking CC→CV switch
IMP_MAX_DIST     = 60       # If nearest impedance cycle is farther than this,
                            # store NaN instead of a potentially stale value


# ── helpers ──────────────────────────────────────────────────────────────────
def _arr(x):
    """Ensure a value is a numpy array (scalar → 1-element array)."""
    a = np.array(x)
    return a.flatten()


def extract_cv_time(charge_data: dict) -> float:
    """
    Return duration (s) of the CV phase in a charge cycle.
    CV phase = everything after Voltage_measured first crosses CV_VOLTAGE_THRESH.
    Returns NaN if the threshold is never crossed.
    """
    volt = _arr(charge_data["Voltage_measured"])
    time = _arr(charge_data["Time"])
    cv_mask = volt >= CV_VOLTAGE_THRESH
    if not cv_mask.any():
        return float("nan")
    cv_start_idx = int(np.argmax(cv_mask))
    return float(time[-1] - time[cv_start_idx])


def extract_discharge_features(discharge_data: dict) -> dict:
    """Extract per-cycle scalar features from one discharge cycle."""
    volt = _arr(discharge_data["Voltage_measured"])
    time = _arr(discharge_data["Time"])
    capacity = float(discharge_data["Capacity"])   # already a scalar

    return {
        "discharge_capacity": capacity,
        "avg_voltage":        float(np.mean(volt)),
        "end_voltage":        float(volt[-1]),
        "discharge_time":     float(time[-1]),
    }


def extract_impedance_features(imp_data: dict) -> dict:
    """Extract Re and Rct from an impedance cycle."""
    return {
        "Re":  float(imp_data.get("Re",  np.nan)),
        "Rct": float(imp_data.get("Rct", np.nan)),
    }


def process_battery(mat_path: Path, eol_ah: float) -> pd.DataFrame:
    """
    Load one .mat file and return a DataFrame with one row per discharge cycle.
    """
    mat = scipy.io.loadmat(str(mat_path), simplify_cells=True)

    # The battery key matches the filename stem (e.g. 'B0005')
    bat_key = mat_path.stem          # 'B0005'
    if bat_key not in mat:
        # fallback: find the first non-dunder key
        bat_key = next(k for k in mat if not k.startswith("_"))

    cycles = mat[bat_key]["cycle"]   # list of dicts

    # ── index all cycle types by their position in the cycle list ────────────
    discharge_cycles  = [(i, c) for i, c in enumerate(cycles) if c["type"] == "discharge"]
    charge_by_pos     = {i: c for i, c in enumerate(cycles) if c["type"] == "charge"}
    impedance_by_pos  = {i: c for i, c in enumerate(cycles) if c["type"] == "impedance"}
    imp_positions     = sorted(impedance_by_pos.keys())
    charge_positions  = sorted(charge_by_pos.keys())

    rows = []
    for dis_pos, dis_cycle in discharge_cycles:
        row = {"battery": mat_path.stem}

        # ── discharge features ───────────────────────────────────────────────
        row.update(extract_discharge_features(dis_cycle["data"]))

        # ── CV charge time: nearest preceding charge cycle ───────────────────
        prec_charges = [p for p in charge_positions if p < dis_pos]
        if prec_charges:
            ch_pos = max(prec_charges)
            row["cv_charge_time"] = extract_cv_time(charge_by_pos[ch_pos]["data"])
        else:
            row["cv_charge_time"] = float("nan")

        # ── Re / Rct: nearest impedance cycle (any direction) ────────────────
        if imp_positions:
            nearest_imp = min(imp_positions, key=lambda x: abs(x - dis_pos))
            dist = abs(nearest_imp - dis_pos)
            if dist <= IMP_MAX_DIST:
                row.update(extract_impedance_features(impedance_by_pos[nearest_imp]["data"]))
            else:
                row["Re"] = row["Rct"] = float("nan")
        else:
            row["Re"] = row["Rct"] = float("nan")

        rows.append(row)

    df = pd.DataFrame(rows)

    # ── cycle index (1-based) ────────────────────────────────────────────────
    df.insert(0, "cycle", range(1, len(df) + 1))

    # ── SOH ─────────────────────────────────────────────────────────────────
    first_cap = df["discharge_capacity"].iloc[0]
    df["SOH"] = df["discharge_capacity"] / first_cap

    # ── RUL ─────────────────────────────────────────────────────────────────
    # EOL = first cycle where capacity drops below eol_ah
    below_eol = df.index[df["discharge_capacity"] < eol_ah].tolist()
    if below_eol:
        eol_cycle_idx = below_eol[0]          # 0-based row index
        df["RUL"] = eol_cycle_idx - df.index  # 0 at EOL, negative after
    else:
        # Battery never reached EOL in this dataset — RUL is open-ended
        # Use distance to last cycle as a lower-bound estimate
        last_idx = len(df) - 1
        df["RUL"] = last_idx - df.index
        print(f"  [{mat_path.stem}] EOL ({eol_ah} Ah) never reached. "
              f"RUL counted from last cycle (lower bound).", file=sys.stderr)

    return df


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Extract per-cycle features from NASA battery .mat files."
    )
    parser.add_argument("mat_files", nargs="+", help=".mat file paths")
    parser.add_argument(
        "--eol", type=float, default=EOL_AH_DEFAULT,
        help=f"End-of-life capacity threshold in Ah (default: {EOL_AH_DEFAULT})"
    )
    parser.add_argument(
        "--out", default="nasa_battery_features.csv",
        help="Output CSV filename (default: nasa_battery_features.csv)"
    )
    args = parser.parse_args()

    all_dfs = []
    for path_str in args.mat_files:
        p = Path(path_str)
        if not p.exists():
            print(f"[WARN] File not found: {p}", file=sys.stderr)
            continue
        print(f"Processing {p.name} ...", file=sys.stderr)
        try:
            df = process_battery(p, eol_ah=args.eol)
            total = len(df)
            eol_row = df[df["RUL"] == 0]
            eol_info = f"EOL @ cycle {eol_row['cycle'].iloc[0]}" if not eol_row.empty else "EOL not reached"
            print(f"  → {total} discharge cycles, {eol_info}", file=sys.stderr)
            all_dfs.append(df)
        except Exception as e:
            print(f"[ERROR] Failed to process {p.name}: {e}", file=sys.stderr)
            raise

    if not all_dfs:
        print("No files processed. Exiting.", file=sys.stderr)
        sys.exit(1)

    combined = pd.concat(all_dfs, ignore_index=True)

    # ── column order ─────────────────────────────────────────────────────────
    cols = [
        "battery", "cycle",
        "discharge_capacity", "avg_voltage", "end_voltage",
        "discharge_time", "cv_charge_time",
        "Re", "Rct",
        "SOH", "RUL"
    ]
    combined = combined[cols]

    out_path = Path(args.out)
    combined.to_csv(out_path, index=False, float_format="%.6f")
    print(f"\nSaved {len(combined)} rows → {out_path}", file=sys.stderr)
    print(combined.head(10).to_string())
    print("\nStats:")
    print(combined.describe().to_string())


if __name__ == "__main__":
    main()
