#!/usr/bin/env python3
import argparse
import csv
import json
import math
from pathlib import Path
from typing import List

import numpy as np


CALIBRATION_FILE = Path("pendulum_calibration.json")


def load_calibration(model_name: str):
    if not CALIBRATION_FILE.exists():
        raise SystemExit(f"Calibration file not found: {CALIBRATION_FILE}")
    with CALIBRATION_FILE.open("r") as f:
        data = json.load(f)

    models = data.get("models", {})
    recommended = data.get("recommended_model")

    if model_name == "auto":
        if recommended is None:
            raise SystemExit(
                "Calibration file does not specify a recommended_model. "
                "Re-run fit_pendulum_calibration.py, or choose --model single/double explicitly."
            )
        model_name = recommended

    if model_name == "single":
        info = models.get("single")
        if not info or "C" not in info:
            raise SystemExit("Single-parameter model not found in calibration file.")
        C = float(info["C"])
        return model_name, {"C": C}

    if model_name == "double":
        info = models.get("double")
        if not info or "A" not in info or "p" not in info:
            raise SystemExit("Two-parameter model not found in calibration file.")
        A = float(info["A"])
        p = float(info["p"])
        return model_name, {"A": A, "p": p}

    raise SystemExit(f"Unknown model name: {model_name}")


def compute_speed_from_angle(theta_deg: float, model_name: str, params: dict) -> float:
    # theta is angle in degrees; convert to radians and use absolute value
    angle_rad = math.radians(abs(theta_deg))
    if angle_rad <= 0:
        return 0.0
    tan_theta = math.tan(angle_rad)
    if tan_theta <= 0:
        return 0.0

    if model_name == "single":
        C = params["C"]
        return C * math.sqrt(tan_theta)
    elif model_name == "double":
        A = params["A"]
        p = params["p"]
        return A * (tan_theta ** p)
    else:
        raise ValueError(f"Unsupported model: {model_name}")


def process_log(in_path: Path, out_path: Path, model_name: str, params: dict, add_both: bool = False):
    with in_path.open("r", newline="") as f_in, out_path.open("w", newline="") as f_out:
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)
        try:
            header = next(reader)
        except StopIteration:
            raise SystemExit(f"Empty CSV file: {in_path}")

        # Identify columns if present
        try:
            idx_gt = header.index("ground_truth_mps")
        except ValueError:
            idx_gt = None
        try:
            idx_student = header.index("student_mps")
        except ValueError:
            idx_student = None

        if idx_student is None:
            raise SystemExit("Input CSV does not contain 'student_mps' column.")

        # Extend header with new columns
        new_cols: List[str] = []
        if add_both:
            new_cols.extend([
                "student_single_mps",
                "student_double_mps",
                "err_single_mps",
                "err_double_mps",
                "err_single_pct",
                "err_double_pct",
            ])
        else:
            new_cols.extend([
                f"student_{model_name}_mps",
                f"err_{model_name}_mps",
                f"err_{model_name}_pct",
            ])
        writer.writerow(header + new_cols)

        for row in reader:
            if not row:
                continue
            if len(row) < len(header):
                # pad short rows
                row = row + ["" for _ in range(len(header) - len(row))]

            # Parse student angle
            theta_str = row[idx_student].strip() if idx_student is not None else ""
            if theta_str:
                try:
                    theta_deg = float(theta_str)
                except ValueError:
                    theta_deg = float("nan")
            else:
                theta_deg = float("nan")

            gt_val = None
            if idx_gt is not None and 0 <= idx_gt < len(row):
                gt_str = row[idx_gt].strip()
                if gt_str:
                    try:
                        gt_val = float(gt_str)
                    except ValueError:
                        gt_val = None

            # Compute speeds and errors
            new_values: List[str] = []
            if add_both:
                # Single model
                try:
                    v_single = compute_speed_from_angle(theta_deg, "single", params["single"])
                except Exception:
                    v_single = float("nan")
                # Double model
                try:
                    v_double = compute_speed_from_angle(theta_deg, "double", params["double"])
                except Exception:
                    v_double = float("nan")

                def err_pair(v_est: float):
                    if gt_val is None or not math.isfinite(v_est):
                        return "", ""
                    err = v_est - gt_val
                    err_pct = (err / gt_val * 100.0) if gt_val != 0 else float("nan")
                    return f"{err:.6f}", f"{err_pct:.3f}"

                es_mps, es_pct = err_pair(v_single)
                ed_mps, ed_pct = err_pair(v_double)

                new_values.extend([
                    f"{v_single:.6f}" if math.isfinite(v_single) else "",
                    f"{v_double:.6f}" if math.isfinite(v_double) else "",
                    es_mps,
                    ed_mps,
                    es_pct,
                    ed_pct,
                ])
            else:
                # Single chosen model
                v_est = compute_speed_from_angle(theta_deg, model_name, params)
                if gt_val is not None and math.isfinite(v_est):
                    err = v_est - gt_val
                    err_pct = (err / gt_val * 100.0) if gt_val != 0 else float("nan")
                    err_str = f"{err:.6f}"
                    err_pct_str = f"{err_pct:.3f}"
                else:
                    err_str = ""
                    err_pct_str = ""
                new_values.extend([
                    f"{v_est:.6f}" if math.isfinite(v_est) else "",
                    err_str,
                    err_pct_str,
                ])

            writer.writerow(row + new_values)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Apply pendulum calibration to a saved CSV log. "
            "Reads pendulum_calibration.json and adds calibrated student speeds "
            "and errors per sample."
        )
    )
    parser.add_argument("log", type=Path, help="Path to CSV log from Testing_mac.py")
    parser.add_argument(
        "--model",
        choices=["auto", "single", "double", "both"],
        default="auto",
        help=(
            "Which model to use: 'single', 'double', 'both' to add both, or "
            "'auto' to use the recommended_model from pendulum_calibration.json "
            "(default: auto)."
        ),
    )

    args = parser.parse_args()
    in_path: Path = args.log
    if not in_path.exists():
        raise SystemExit(f"Log file not found: {in_path}")

    # Load calibration
    if args.model == "both":
        # For both, we need parameters for both models
        _, single_params = load_calibration("single")
        _, double_params = load_calibration("double")
        params = {"single": single_params, "double": double_params}
        model_name = "both"
    else:
        model_name, params = load_calibration(args.model)

    # Determine output path
    out_path = in_path.with_name(in_path.stem + "_calibrated" + in_path.suffix)

    print(f"Input log:     {in_path.resolve()}")
    print(f"Output log:    {out_path.resolve()}")
    if model_name == "both":
        print("Using both models: single and double")
    else:
        print(f"Using model:   {model_name}")

    process_log(in_path, out_path, model_name, params, add_both=(model_name == "both"))
    print("Done.")


if __name__ == "__main__":
    main()
