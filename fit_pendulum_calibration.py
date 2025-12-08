#!/usr/bin/env python3
import argparse
import csv
import json
import math
from pathlib import Path
from typing import List, Tuple

import numpy as np


def load_aligned_log(csv_path: Path) -> Tuple[np.ndarray, np.ndarray]:
    """Load ground truth speed and student angle from an aligned CSV log.

    Expects the fixed-rate aligned format produced by Testing_mac.py when two
    devices are present and log_rate_hz is set, with columns:
        timestamp_iso, timestamp_epoch, ground_truth_mps, student_mps, ...

    During calibration runs, student_mps is interpreted as pendulum angle in
    degrees.
    """
    with csv_path.open("r", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            raise RuntimeError(f"Empty CSV file: {csv_path}")

        try:
            idx_gt = header.index("ground_truth_mps")
            idx_student = header.index("student_mps")
        except ValueError as e:
            raise RuntimeError(
                "CSV does not contain required columns 'ground_truth_mps' and "
                "'student_mps'. Make sure you used Testing_mac.py with two "
                "devices and fixed-rate logging enabled."
            ) from e

        gt_vals: List[float] = []
        student_vals: List[float] = []
        for row in reader:
            if not row or len(row) <= max(idx_gt, idx_student):
                continue
            gt_str = row[idx_gt].strip()
            st_str = row[idx_student].strip()
            if not gt_str or not st_str:
                continue
            try:
                v_gt = float(gt_str)
                theta_deg = float(st_str)
            except ValueError:
                continue
            gt_vals.append(v_gt)
            student_vals.append(theta_deg)

    if not gt_vals:
        raise RuntimeError(f"No valid data rows found in {csv_path}")

    return np.asarray(student_vals, dtype=float), np.asarray(gt_vals, dtype=float)


def _filter_data(
    theta_deg: np.ndarray,
    v_gt: np.ndarray,
    min_speed: float = 0.5,
    min_angle_deg: float = 0.2,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Apply basic filtering and compute tan(theta) and sqrt(tan(theta)).

    Returns (theta_deg_f, v_gt_f, tan_theta, sqrt_tan_theta).
    """
    theta = np.asarray(theta_deg, dtype=float)
    v = np.asarray(v_gt, dtype=float)

    mask = np.isfinite(theta) & np.isfinite(v)
    theta = theta[mask]
    v = v[mask]

    theta_rad = np.abs(np.deg2rad(theta))
    tan_theta = np.tan(theta_rad)

    mask = (
        (theta_rad >= math.radians(min_angle_deg))
        & (tan_theta > 0)
        & (v >= min_speed)
    )
    theta_f = theta[mask]
    v_f = v[mask]
    tan_f = tan_theta[mask]
    sqrt_tan_f = np.sqrt(tan_f)

    if tan_f.size < 3:
        raise RuntimeError(
            "Not enough valid samples after filtering. "
            "Try lowering min_speed or min_angle_deg, or collect more data."
        )

    return theta_f, v_f, tan_f, sqrt_tan_f


def _compute_metrics(v_true: np.ndarray, v_pred: np.ndarray) -> dict:
    err = v_pred - v_true
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    with np.errstate(divide="ignore", invalid="ignore"):
        mape = np.abs(err) / np.maximum(np.abs(v_true), 1e-9)
        mape = float(np.mean(mape) * 100.0)
    return {"mae": mae, "rmse": rmse, "mape_pct": mape}


def fit_single_parameter(
    theta_deg: np.ndarray, v_gt: np.ndarray, min_speed: float, min_angle_deg: float
) -> Tuple[float, dict]:
    """Fit single-parameter model V = C * sqrt(tan(|theta|))."""
    _, v_f, tan_f, sqrt_tan_f = _filter_data(theta_deg, v_gt, min_speed, min_angle_deg)

    num = float(np.dot(sqrt_tan_f, v_f))
    den = float(np.dot(sqrt_tan_f, sqrt_tan_f))
    if den <= 0:
        raise RuntimeError("Degenerate data: denominator for C is non-positive.")
    C = num / den

    v_pred = C * sqrt_tan_f
    metrics = _compute_metrics(v_f, v_pred)
    return C, metrics


def fit_two_parameter(
    theta_deg: np.ndarray, v_gt: np.ndarray, min_speed: float, min_angle_deg: float
) -> Tuple[Tuple[float, float], dict]:
    """Fit two-parameter model V = A * (tan(|theta|))**p via log-space regression."""
    _, v_f, tan_f, _ = _filter_data(theta_deg, v_gt, min_speed, min_angle_deg)

    # Use only strictly positive values for log-space fitting
    mask = (tan_f > 0) & (v_f > 0)
    tan_pos = tan_f[mask]
    v_pos = v_f[mask]
    if tan_pos.size < 3:
        raise RuntimeError("Not enough positive samples for two-parameter fit.")

    z = np.log(tan_pos)
    w = np.log(v_pos)

    # Linear regression: w = a + p * z
    X = np.vstack([np.ones_like(z), z]).T
    beta, *_ = np.linalg.lstsq(X, w, rcond=None)
    a = float(beta[0])
    p = float(beta[1])
    A = float(math.exp(a))

    v_pred = A * (tan_pos ** p)
    metrics = _compute_metrics(v_pos, v_pred)
    return (A, p), metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fit calibration models relating pendulum angle (student) "
            "to ground-truth wind speed using saved CSV logs."
        )
    )
    parser.add_argument("log", type=Path, help="Path to aligned CSV log from Testing_mac.py")
    parser.add_argument(
        "--min-speed",
        type=float,
        default=0.5,
        help="Minimum ground-truth speed (m/s) to include in fit (default: 0.5)",
    )
    parser.add_argument(
        "--min-angle-deg",
        type=float,
        default=0.2,
        help="Minimum absolute angle in degrees to include in fit (default: 0.2)",
    )
    parser.add_argument(
        "--models",
        choices=["single", "double", "both"],
        default="both",
        help="Which models to fit (default: both)",
    )

    args = parser.parse_args()

    csv_path: Path = args.log
    if not csv_path.exists():
        raise SystemExit(f"CSV log not found: {csv_path}")

    print(f"Loading data from: {csv_path}")
    theta_deg, v_gt = load_aligned_log(csv_path)
    print(f"Loaded {theta_deg.size} samples (student angle deg, ground_truth_mps)")

    results = {}

    if args.models in ("single", "both"):
        print("\nFitting single-parameter model: V = C * sqrt(tan(|theta|))")
        try:
            C, metrics = fit_single_parameter(theta_deg, v_gt, args.min_speed, args.min_angle_deg)
            results["single"] = {
                "C": C,
                "metrics": metrics,
                "model": "V = C * sqrt(tan(|theta|))",
                "min_speed": args.min_speed,
                "min_angle_deg": args.min_angle_deg,
            }
            print(f"  C = {C:.6f}")
            print(
                f"  RMSE = {metrics['rmse']:.4f} m/s, "
                f"MAE = {metrics['mae']:.4f} m/s, "
                f"MAPE = {metrics['mape_pct']:.2f}%"
            )
        except RuntimeError as e:
            print(f"  Single-parameter fit failed: {e}")

    if args.models in ("double", "both"):
        print("\nFitting two-parameter model: V = A * (tan(|theta|))**p")
        try:
            (A, p), metrics = fit_two_parameter(theta_deg, v_gt, args.min_speed, args.min_angle_deg)
            results["double"] = {
                "A": A,
                "p": p,
                "metrics": metrics,
                "model": "V = A * (tan(|theta|))**p",
                "min_speed": args.min_speed,
                "min_angle_deg": args.min_angle_deg,
            }
            print(f"  A = {A:.6f}, p = {p:.4f}")
            print(
                f"  RMSE = {metrics['rmse']:.4f} m/s, "
                f"MAE = {metrics['mae']:.4f} m/s, "
                f"MAPE = {metrics['mape_pct']:.2f}%"
            )
        except RuntimeError as e:
            print(f"  Two-parameter fit failed: {e}")

    if not results:
        raise SystemExit("No successful fits. See messages above for details.")

    # Decide a recommended model based on RMSE (lower is better)
    best_name = None
    best_rmse = None
    for name, info in results.items():
        rmse = info["metrics"]["rmse"]
        if best_rmse is None or rmse < best_rmse:
            best_rmse = rmse
            best_name = name

    print(f"\nRecommended model based on RMSE: {best_name} (RMSE={best_rmse:.4f} m/s)")

    # Prepare JSON payload. Keep backward-compatible 'calibration_constant'
    # for the single-parameter model so pi_pendulum_angle.py can continue to
    # use it directly, while also storing full details for both models.
    payload = {
        "calibration_constant": results.get("single", {}).get("C", 1.0),
        "models": results,
        "recommended_model": best_name,
    }

    out_path = Path("pendulum_calibration.json")
    with out_path.open("w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    print(f"\nSaved calibration to {out_path.resolve()}")


if __name__ == "__main__":
    main()
