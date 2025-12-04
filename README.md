# Raspberry Pi Pendulum Wind Speed Sensor

Computer vision-based pendulum tracking system that converts pendulum angle to wind speed using `V = C × √(tan(θ))`.

## Quick Start

```bash
# Setup
./setup_raspberry_pi.sh

# Calibrate (once)
python calibrate_pendulum.py

# Run
python pi_pendulum_angle.py
```

**Interactive:** Left-click on colored marker to track. Press 'q' to quit.

## Installation

```bash
git clone <repo-url>
cd comp0219_cw2
chmod +x setup_raspberry_pi.sh
./setup_raspberry_pi.sh
```

## Usage

```bash
# Default: Wind speed output over UART
python pi_pendulum_angle.py

# Angle mode
python pi_pendulum_angle.py --angle

# Fast motion mode
python pi_pendulum_angle.py --fast

# Custom calibration
python pi_pendulum_angle.py -C 2.5

# Disable serial
python pi_pendulum_angle.py --serial none
```

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--angle` | Output angle instead of wind speed | Wind speed |
| `-C VALUE` | Calibration constant | From file or 1.0 |
| `--fast` | Fast motion tracking | Off |
| `--serial PORT` | Serial port | `/dev/ttyAMA0` |
| `--baud RATE` | Baud rate | 115200 |

## Calibration

```bash
# Interactive: Enter angle/wind pairs
python calibrate_pendulum.py

# From CSV file
python calibrate_pendulum.py --file data.csv

# Single measurement
python calibrate_pendulum.py --angle 15.5 --wind 3.2

# View current
python calibrate_pendulum.py --show
```

Saves to `pendulum_calibration.json` and auto-loads on next run.

## Output

**Wind speed:** `3.2` (just number)  
**Angle mode:** `angle:15.3`  
**UART:** Same format with `\r\n`

## Troubleshooting

**Camera not working:**
```bash
libcamera-hello
sudo raspi-config  # Enable camera
```

**Permission denied:**
```bash
sudo usermod -a -G dialout,video,gpio $USER
# Logout and login
```

**Tracking fails:** Click to re-select color, improve lighting, use `--fast` mode.

## Requirements

- Raspberry Pi 4 (3B+ works)
- Pi Camera Module v2/v3
- Pendulum with 2 colored markers
- Python 3.10+

## Files

- `pi_pendulum_angle.py` - Main tracker
- `calibrate_pendulum.py` - Calibration tool
- `setup_raspberry_pi.sh` - Automated setup
- `requirements_raspberry_pi.txt` - Dependencies

See [CALIBRATION_README.md](CALIBRATION_README.md) for detailed calibration guide.

