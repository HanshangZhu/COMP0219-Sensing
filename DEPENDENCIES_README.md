# Raspberry Pi Dependencies for comp0219_cw2

This document provides a complete overview of all Python dependencies needed to run this project on Raspberry Pi.

## Quick Start

```bash
# On your Raspberry Pi, run:
chmod +x setup_raspberry_pi.sh
./setup_raspberry_pi.sh

# OR manually:
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements_raspberry_pi.txt
```

## Complete Dependency List

### From Your Conda Environment (`comp0219`)

These packages are already installed in your Windows development environment:

| Package | Version | Purpose |
|---------|---------|---------|
| `numpy` | 2.2.6 | Numerical operations, array handling |
| `opencv-python` | 4.12.0.88 | Computer vision, image processing |
| `opencv-contrib-python` | 4.12.0.88 | Camera calibration, advanced CV features |
| `pyserial` | 3.5 | UART/Serial communication with STM32 |
| `PySide6` | 6.10.1 | Qt6 GUI framework (main) |
| `PySide6-Essentials` | 6.10.1 | Qt6 core modules |
| `PySide6-Addons` | 6.10.1 | Qt6 additional widgets |
| `shiboken6` | 6.10.1 | Qt6 Python bindings |
| `pyqtgraph` | 0.14.0 | Real-time plotting and graphing |
| `PyYAML` | 6.0.3 | YAML config file parsing |
| `colorama` | 0.4.6 | Colored terminal output |

### Raspberry Pi-Specific Packages

Additional packages needed for Raspberry Pi hardware and camera support:

| Package | Purpose | Used By |
|---------|---------|---------|
| `picamera2` | Raspberry Pi Camera Module interface | `pi_pendulum_angle.py`, Week 8 & 9 tutorials |
| `pidng` | RAW DNG image format support | Camera calibration |
| `piexif` | EXIF metadata handling | Image capture scripts |
| `Pillow` | Image manipulation library | Various scripts |
| `simplejpeg` | Fast JPEG encoding/decoding | Real-time video processing |
| `av` | PyAV video/audio processing | Video recording |
| `python-v4l2` | Video4Linux2 camera control | Low-level camera access |
| `python-prctl` | Process control for RT scheduling | `RT_Kernel_Test_Scripts/TestingTiming.py` |
| `jsonschema` | JSON schema validation | Configuration validation |
| `attrs` | Python class utilities | Data structures |
| `pyrsistent` | Immutable data structures | Configuration management |
| `tqdm` | Progress bars | Long operations |
| `libarchive-c` | Archive handling | File operations |

## Script-to-Dependency Mapping

### Main Scripts

| Script | Required Packages |
|--------|------------------|
| `CameraTest.py` | `pyserial` |
| `pendulum_angle.py` | `opencv-python`, `numpy` |
| `pi_pendulum_angle.py` | `picamera2`, `opencv-python`, `numpy` |

### LiveGraphing Folder

| Script | Required Packages |
|--------|------------------|
| `Testing_Windows.py` | `PySide6`, `pyqtgraph`, `pyserial`, `PyYAML` |
| `Testing_mac.py` | `PySide6`, `pyqtgraph`, `pyserial`, `PyYAML` |

### Week 7: Camera Calibration

| Script | Required Packages |
|--------|------------------|
| `calibration.py` | `opencv-python`, `opencv-contrib-python`, `numpy` |
| `calibration_cap.py` | `opencv-python`, `opencv-contrib-python`, `numpy` |

### Week 8: Color Segmentation

| Script | Required Packages |
|--------|------------------|
| `minimal_example.py` | `opencv-python`, `numpy`, `[picamera2]` |
| `hsv_vs_rgb_comparison.py` | `opencv-python`, `numpy` |
| `get_coordinates.py` | `opencv-python`, `numpy` |

### Week 9: Line Fitting

| Script | Required Packages |
|--------|------------------|
| `minimal_line_fitting.py` | `opencv-python`, `numpy`, `[picamera2]` |

### RT Kernel Test Scripts

| Script | Required Packages |
|--------|------------------|
| `TestingTiming.py` | `pyserial`, `python-prctl` |

## System Prerequisites

Before installing Python packages, ensure these system packages are installed:

```bash
# Core development tools
sudo apt install -y python3-pip python3-venv python3-dev git
sudo apt install -y build-essential cmake pkg-config

# Scientific computing libraries
sudo apt install -y libatlas-base-dev libhdf5-dev libhdf5-serial-dev

# Image processing libraries
sudo apt install -y libjpeg-dev zlib1g-dev libfreetype6-dev
sudo apt install -y liblcms2-dev libopenjp2-7 libtiff5
sudo apt install -y libwebp-dev libpng-dev

# Video device support
sudo apt install -y libv4l-dev v4l-utils

# Qt6 for GUI
sudo apt install -y qt6-base-dev libqt6gui6 libqt6widgets6

# Real-time support
sudo apt install -y libcap-dev

# Raspberry Pi Camera (recommended to install system-wide)
sudo apt install -y python3-picamera2 python3-libcamera python3-kms++
```

## Hardware Configuration

### 1. Camera Permissions

```bash
sudo usermod -a -G video $USER
sudo usermod -a -G gpio $USER
# Logout and login again
```

### 2. Serial Port Permissions

```bash
sudo usermod -a -G dialout $USER
# Logout and login again
```

### 3. Enable UART (for `CameraTest.py`)

Edit `/boot/config.txt` or `/boot/firmware/config.txt`:

```
enable_uart=1
dtoverlay=disable-bt
```

Then:

```bash
sudo systemctl disable hciuart
sudo reboot
```

### 4. Verify UART

```bash
# Check if UART is enabled
ls -l /dev/ttyAMA0

# Test with minicom (optional)
sudo apt install -y minicom
minicom -b 115200 -o -D /dev/ttyAMA0
```

## Installation Tips

### Option 1: Use System Packages (Recommended)

For packages like OpenCV and picamera2 that take long to compile:

```bash
sudo apt install -y python3-opencv python3-picamera2
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements_raspberry_pi.txt
```

### Option 2: Pure Virtual Environment

Fully isolated environment (longer installation time):

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_raspberry_pi.txt
# Note: OpenCV compilation may take 20-40 minutes on Raspberry Pi 4
```

## Verification

After installation, verify all packages:

```bash
source venv/bin/activate

# Test core packages
python3 -c "import cv2; print('OpenCV:', cv2.__version__)"
python3 -c "import numpy; print('NumPy:', numpy.__version__)"
python3 -c "import serial; print('PySerial:', serial.VERSION)"
python3 -c "import yaml; print('PyYAML: OK')"
python3 -c "from PySide6 import QtCore; print('PySide6:', QtCore.__version__)"
python3 -c "import pyqtgraph; print('pyqtgraph: OK')"

# Test Pi-specific packages
python3 -c "from picamera2 import Picamera2; print('picamera2: OK')"
```

## Troubleshooting

### OpenCV Installation Fails

```bash
# Use pre-compiled system package instead
sudo apt install -y python3-opencv
# Create venv with system packages
python3 -m venv --system-site-packages venv
```

### picamera2 Not Found

```bash
# Install system-wide and use --system-site-packages
sudo apt install -y python3-picamera2
```

### Permission Denied on `/dev/ttyAMA0`

```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
# Logout and login again
```

### Import Error: libQt6Core.so

```bash
# Install Qt6 system libraries
sudo apt install -y qt6-base-dev libqt6gui6 libqt6widgets6
```

### Real-time Scheduling Fails

```bash
# Give Python permission for real-time scheduling
sudo setcap cap_sys_nice+ep $(which python3)
# OR run scripts with sudo (not recommended)
```

## Hardware Requirements

- **Minimum**: Raspberry Pi 3B+ (may struggle with CV operations)
- **Recommended**: Raspberry Pi 4 (4GB RAM) or Raspberry Pi 5
- **Camera**: Raspberry Pi Camera Module v2, v3, or HQ Camera
- **Accessories**: UART-capable device (STM32, Arduino) for serial communication

## Memory Optimization

If running on Pi 3 or low-memory Pi 4:

1. Reduce camera resolution in scripts (e.g., 640x480 instead of 1280x720)
2. Close unnecessary applications
3. Increase swap size:
   ```bash
   sudo dphys-swapfile swapoff
   sudo nano /etc/dphys-swapfile
   # Set CONF_SWAPSIZE=1024
   sudo dphys-swapfile setup
   sudo dphys-swapfile swapon
   ```

## License and Credits

This project is for educational purposes as part of COMP0219 coursework.

---

**Last Updated**: December 2025

