# Pendulum Wind Speed Sensor - Calibration Guide

This guide explains how to calibrate your pendulum wind speed sensor to get accurate wind speed readings.

## Overview

The pendulum wind speed sensor uses the formula:
```
V = C × √(tan(θ))
```

Where:
- **V** = Wind speed (m/s)
- **C** = Calibration constant (what we need to find)
- **θ** = Pendulum angle (degrees)

## Quick Start

### 1. Collect Calibration Data

You need paired measurements of:
- **Pendulum angle** (from your sensor)
- **Ground truth wind speed** (from a reference anemometer)

Collect at least 5-10 measurements at different wind speeds for best results.

### 2. Run Calibration (Interactive Mode)

```bash
python calibrate_pendulum.py
```

Example session:
```
Measurement 1 - Angle (degrees): 15.5
Measurement 1 - Wind speed (m/s): 3.2
  → C for this sample: 1.234567

Measurement 2 - Angle (degrees): 20.1
Measurement 2 - Wind speed (m/s): 4.5
  → C for this sample: 1.256789

(type 'done' when finished)
Measurement 3 - Angle (degrees): done

CALIBRATION RESULTS
Number of measurements: 2
Average C: 1.245678
```

The calibration constant is automatically saved to `pendulum_calibration.json`.

### 3. Use Your Calibrated Sensor

```bash
# Automatically uses saved calibration
python pi_pendulum_angle.py
```

That's it! The sensor will now output calibrated wind speed values.

## Calibration Methods

### Method 1: Interactive Mode (Recommended)

Enter measurements one by one:

```bash
python calibrate_pendulum.py
```

### Method 2: Batch Mode (CSV File)

Create a CSV file with your measurements:

**measurements.csv:**
```csv
angle,wind_speed
15.5,3.2
20.1,4.5
18.3,3.9
22.7,5.1
16.2,3.5
```

Run calibration:
```bash
python calibrate_pendulum.py --file measurements.csv
```

### Method 3: Single Measurement

Quick calibration from one measurement:

```bash
python calibrate_pendulum.py --angle 15.5 --wind 3.2
```

### Method 4: View Current Calibration

Check what calibration is currently saved:

```bash
python calibrate_pendulum.py --show
```

## Best Practices

### Collecting Good Calibration Data

1. **Multiple wind speeds**: Collect measurements across your expected wind speed range (e.g., 2-10 m/s)

2. **Steady conditions**: Take measurements when wind is relatively steady (not gusting)

3. **Reference anemometer**: Use a calibrated reference sensor positioned near your pendulum

4. **Same setup**: Calibrate with the final setup (same pendulum length, bob weight, etc.)

5. **Multiple samples**: 10-20 measurements give better accuracy than 2-3

### Example Calibration Session

```bash
# Collect data with your setup alongside a reference anemometer
# Record: angle from pendulum, wind speed from reference

# Save measurements to CSV
echo "angle,wind_speed" > my_calibration.csv
echo "12.3,2.5" >> my_calibration.csv
echo "15.7,3.2" >> my_calibration.csv
echo "18.2,3.8" >> my_calibration.csv
echo "21.5,4.6" >> my_calibration.csv
echo "25.1,5.4" >> my_calibration.csv

# Run calibration
python calibrate_pendulum.py --file my_calibration.csv

# Test it
python pi_pendulum_angle.py
```

## File Structure

### pendulum_calibration.json

The calibration file stores:
```json
{
  "calibration_constant": 1.245678,
  "angle_measurements": [15.5, 20.1, 18.3],
  "wind_measurements": [3.2, 4.5, 3.9],
  "num_samples": 3,
  "notes": "Calibrated outdoors, light wind"
}
```

## Using Calibration with pi_pendulum_angle.py

### Default Behavior (Automatic)

```bash
# Loads calibration from pendulum_calibration.json automatically
python pi_pendulum_angle.py
```

**Priority order:**
1. Command-line argument (`-C`)
2. Calibration file (`pendulum_calibration.json`)
3. Default fallback (`C = 1.0`)

### Override Calibration

```bash
# Use custom value (ignores saved calibration)
python pi_pendulum_angle.py -C 1.5
```

### Disable Calibration

```bash
# Use default C = 1.0
python pi_pendulum_angle.py -C 1.0
```

## Troubleshooting

### "No calibration found"

The file `pendulum_calibration.json` doesn't exist. Run `calibrate_pendulum.py` first.

### Wildly Inaccurate Results

Possible causes:
- **Wrong units**: Ensure angles are in degrees, wind speed in m/s
- **Too few samples**: Use at least 5-10 measurements
- **Bad reference data**: Check your reference anemometer
- **Different setup**: Recalibrate if you change pendulum length/weight

### Calibration file corrupted

Delete `pendulum_calibration.json` and recalibrate:
```bash
rm pendulum_calibration.json
python calibrate_pendulum.py
```

## Mathematical Background

### Deriving the Calibration Constant

From the formula `V = C × √(tan(θ))`, we can solve for C:

```
C = V / √(tan(θ))
```

For multiple measurements, we calculate C for each pair and take the average:

```
C_avg = (1/n) × Σ(V_i / √(tan(θ_i)))
```

This gives us the best-fit calibration constant for our specific pendulum setup.

### Why Calibration is Needed

The constant C depends on:
- **Pendulum length**
- **Bob mass and shape**
- **Air resistance coefficients**
- **Mechanical friction**
- **Pivot stiffness**

Each physical setup is unique, so calibration is essential for accurate measurements.

## Example Workflow

### Full Calibration and Deployment

```bash
# 1. Collect calibration data
#    (Use pi_pendulum_angle.py in --angle mode alongside reference sensor)
python pi_pendulum_angle.py --angle > angles.txt

# 2. Create CSV with angles and reference wind speeds
# (manually or with script)

# 3. Run calibration
python calibrate_pendulum.py --file calibration_data.csv

# 4. Deploy calibrated sensor
python pi_pendulum_angle.py --serial /dev/ttyAMA0

# Wind speed values are now calibrated!
```

## Advanced: Recalibration

If conditions change (different setup, wear over time), recalibrate:

```bash
# Collect new data
python calibrate_pendulum.py

# This overwrites pendulum_calibration.json with new values
```

Keep old calibrations by renaming the file:
```bash
mv pendulum_calibration.json calibration_backup_2025-12-04.json
python calibrate_pendulum.py
```

---

**Questions?** Check the code comments in `calibrate_pendulum.py` for implementation details.

