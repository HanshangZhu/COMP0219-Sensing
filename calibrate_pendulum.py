#!/usr/bin/env python3
"""
Pendulum Calibration Script
Calculates the calibration constant C for the formula: V = C * sqrt(tan(angle))
"""
import json
import math
import sys
from pathlib import Path

CALIBRATION_FILE = "pendulum_calibration.json"

def calculate_calibration_constant(angle_deg, wind_speed_mps):
    """
    Calculate calibration constant from angle and ground truth wind speed.
    
    Formula: V = C * sqrt(tan(angle))
    Therefore: C = V / sqrt(tan(angle))
    
    Args:
        angle_deg: Measured pendulum angle in degrees
        wind_speed_mps: Ground truth wind speed in m/s
        
    Returns:
        Calibration constant C
    """
    if angle_deg <= 0:
        raise ValueError("Angle must be positive")
    if wind_speed_mps <= 0:
        raise ValueError("Wind speed must be positive")
    
    # Convert to radians
    angle_rad = math.radians(angle_deg)
    
    # Calculate C = V / sqrt(tan(angle))
    tan_angle = math.tan(angle_rad)
    if tan_angle <= 0:
        raise ValueError("tan(angle) must be positive")
    
    C = wind_speed_mps / math.sqrt(tan_angle)
    return C


def save_calibration(C, angle_measurements, wind_measurements, notes=""):
    """
    Save calibration constant to file.
    
    Args:
        C: Calibration constant
        angle_measurements: List of angle measurements used
        wind_measurements: List of wind speed measurements used
        notes: Optional notes about calibration conditions
    """
    calibration_data = {
        "calibration_constant": C,
        "angle_measurements": angle_measurements,
        "wind_measurements": wind_measurements,
        "num_samples": len(angle_measurements),
        "notes": notes
    }
    
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(calibration_data, f, indent=2)
    
    print(f"✓ Calibration saved to {CALIBRATION_FILE}")
    print(f"  Calibration constant C = {C:.6f}")
    print(f"  Based on {len(angle_measurements)} measurements")


def load_calibration():
    """
    Load calibration constant from file.
    
    Returns:
        Calibration constant C, or None if file doesn't exist
    """
    try:
        with open(CALIBRATION_FILE, 'r') as f:
            data = json.load(f)
        return data.get("calibration_constant")
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        print(f"Warning: {CALIBRATION_FILE} is corrupted")
        return None


def interactive_calibration():
    """
    Interactive mode: prompt user for measurements and calculate C
    """
    print("=" * 60)
    print("PENDULUM CALIBRATION - INTERACTIVE MODE")
    print("=" * 60)
    print()
    print("This script will calculate the calibration constant C")
    print("Formula: V = C * sqrt(tan(angle))")
    print()
    print("You need paired measurements of:")
    print("  - Pendulum angle (degrees)")
    print("  - Ground truth wind speed (m/s)")
    print()
    
    angles = []
    winds = []
    
    print("Enter measurements (type 'done' when finished):")
    print()
    
    while True:
        try:
            # Get angle
            angle_input = input(f"Measurement {len(angles)+1} - Angle (degrees): ").strip()
            if angle_input.lower() == 'done':
                break
            angle = float(angle_input)
            
            # Get wind speed
            wind_input = input(f"Measurement {len(angles)+1} - Wind speed (m/s): ").strip()
            wind = float(wind_input)
            
            # Calculate C for this pair
            C_sample = calculate_calibration_constant(angle, wind)
            print(f"  → C for this sample: {C_sample:.6f}")
            print()
            
            angles.append(angle)
            winds.append(wind)
            
        except ValueError as e:
            print(f"Error: {e}. Please try again.")
            print()
        except KeyboardInterrupt:
            print("\nCalibration cancelled.")
            sys.exit(0)
    
    if len(angles) == 0:
        print("No measurements entered. Exiting.")
        sys.exit(0)
    
    # Calculate average C
    C_values = [calculate_calibration_constant(a, w) for a, w in zip(angles, winds)]
    C_avg = sum(C_values) / len(C_values)
    C_std = math.sqrt(sum((c - C_avg)**2 for c in C_values) / len(C_values)) if len(C_values) > 1 else 0
    
    print()
    print("=" * 60)
    print("CALIBRATION RESULTS")
    print("=" * 60)
    print(f"Number of measurements: {len(angles)}")
    print(f"Average C: {C_avg:.6f}")
    if len(C_values) > 1:
        print(f"Standard deviation: {C_std:.6f}")
        print(f"C range: {min(C_values):.6f} to {max(C_values):.6f}")
    print()
    
    # Ask for notes
    notes = input("Optional notes (e.g., weather conditions, setup): ").strip()
    
    # Save
    save_calibration(C_avg, angles, winds, notes)
    print()
    print("Calibration complete! Use this constant with:")
    print(f"  python pi_pendulum_angle.py")
    print("(It will automatically load the saved constant)")


def batch_calibration(data_file):
    """
    Batch mode: load measurements from CSV file
    
    CSV format: angle,wind_speed
    Example:
      15.5,3.2
      20.1,4.5
      25.3,5.8
    """
    import csv
    
    angles = []
    winds = []
    
    try:
        with open(data_file, 'r') as f:
            reader = csv.reader(f)
            # Skip header if present
            first_row = next(reader)
            try:
                angles.append(float(first_row[0]))
                winds.append(float(first_row[1]))
            except ValueError:
                pass  # Was a header row
            
            for row in reader:
                if len(row) >= 2:
                    angles.append(float(row[0]))
                    winds.append(float(row[1]))
        
        if len(angles) == 0:
            print(f"No valid measurements found in {data_file}")
            sys.exit(1)
        
        # Calculate average C
        C_values = [calculate_calibration_constant(a, w) for a, w in zip(angles, winds)]
        C_avg = sum(C_values) / len(C_values)
        
        print(f"Loaded {len(angles)} measurements from {data_file}")
        print(f"Calculated calibration constant: C = {C_avg:.6f}")
        
        save_calibration(C_avg, angles, winds, f"Loaded from {data_file}")
        
    except FileNotFoundError:
        print(f"Error: File '{data_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Calibrate pendulum wind speed sensor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (enter measurements manually)
  python calibrate_pendulum.py
  
  # Batch mode (load from CSV file)
  python calibrate_pendulum.py --file measurements.csv
  
  # Quick calculation from single measurement
  python calibrate_pendulum.py --angle 15.5 --wind 3.2
  
  # View current calibration
  python calibrate_pendulum.py --show

CSV file format:
  angle,wind_speed
  15.5,3.2
  20.1,4.5
  25.3,5.8
        """
    )
    
    parser.add_argument('--angle', type=float,
                       help='Single angle measurement (degrees)')
    parser.add_argument('--wind', type=float,
                       help='Single wind speed measurement (m/s)')
    parser.add_argument('--file', type=str,
                       help='CSV file with angle,wind_speed pairs')
    parser.add_argument('--show', action='store_true',
                       help='Show current calibration')
    
    args = parser.parse_args()
    
    # Show current calibration
    if args.show:
        C = load_calibration()
        if C is None:
            print("No calibration found.")
            print(f"Expected file: {CALIBRATION_FILE}")
        else:
            print(f"Current calibration constant: C = {C:.6f}")
            try:
                with open(CALIBRATION_FILE, 'r') as f:
                    data = json.load(f)
                print(f"Based on {data.get('num_samples', 0)} measurements")
                if data.get('notes'):
                    print(f"Notes: {data['notes']}")
            except:
                pass
        sys.exit(0)
    
    # Single measurement mode
    if args.angle is not None or args.wind is not None:
        if args.angle is None or args.wind is None:
            print("Error: Both --angle and --wind must be provided")
            sys.exit(1)
        
        try:
            C = calculate_calibration_constant(args.angle, args.wind)
            print(f"Calibration constant: C = {C:.6f}")
            print(f"(Based on angle={args.angle}°, wind={args.wind} m/s)")
            
            response = input("Save this calibration? [y/N]: ").strip().lower()
            if response == 'y':
                save_calibration(C, [args.angle], [args.wind], "Single measurement")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        sys.exit(0)
    
    # Batch mode
    if args.file:
        batch_calibration(args.file)
        sys.exit(0)
    
    # Default: Interactive mode
    interactive_calibration()


if __name__ == "__main__":
    main()

