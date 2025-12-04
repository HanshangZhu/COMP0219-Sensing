#!/bin/bash
# ============================================================
# Raspberry Pi Setup Script for comp0219_cw2
# ============================================================
# This script automates the setup of your Python environment
# and system dependencies on Raspberry Pi.
#
# Usage: 
#   chmod +x setup_raspberry_pi.sh
#   ./setup_raspberry_pi.sh
# ============================================================

set -e  # Exit on error

echo "============================================================"
echo "Raspberry Pi Setup for comp0219_cw2"
echo "============================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    print_warning "This script is designed for Raspberry Pi. Continuing anyway..."
fi

# ============================================================
# 1. Update System
# ============================================================
echo ""
echo "Step 1: Updating system packages..."
sudo apt update
sudo apt upgrade -y
print_status "System updated"

# ============================================================
# 2. Install System Dependencies
# ============================================================
echo ""
echo "Step 2: Installing system dependencies..."

# Core development tools
sudo apt install -y python3-pip python3-venv python3-dev git

# Build essentials
sudo apt install -y build-essential cmake pkg-config

# Linear algebra and scientific computing
sudo apt install -y libatlas-base-dev libhdf5-dev libhdf5-serial-dev

# Image processing libraries
sudo apt install -y libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev
sudo apt install -y libopenjp2-7 libtiff5 libwebp-dev libpng-dev

# Video device support
sudo apt install -y libv4l-dev v4l-utils

# Qt6 for GUI (PySide6)
sudo apt install -y qt6-base-dev libqt6gui6 libqt6widgets6

# Real-time support
sudo apt install -y libcap-dev

print_status "System dependencies installed"

# ============================================================
# 3. Install picamera2 (system-wide recommended)
# ============================================================
echo ""
echo "Step 3: Installing picamera2..."
if command -v raspistill &> /dev/null; then
    print_status "Raspberry Pi camera tools detected"
    sudo apt install -y python3-picamera2 python3-libcamera python3-kms++
    print_status "picamera2 installed (system-wide)"
else
    print_warning "Camera tools not found. Install picamera2 manually if needed."
fi

# ============================================================
# 4. Create Python Virtual Environment
# ============================================================
echo ""
echo "Step 4: Creating Python virtual environment..."

# Use --system-site-packages to access system picamera2 and opencv
if [ -d "venv" ]; then
    print_warning "Virtual environment already exists. Skipping creation."
else
    python3 -m venv --system-site-packages venv
    print_status "Virtual environment created with system site packages"
fi

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
print_status "pip upgraded"

# ============================================================
# 5. Install Python Dependencies
# ============================================================
echo ""
echo "Step 5: Installing Python packages..."

if [ -f "requirements_raspberry_pi.txt" ]; then
    print_status "Found requirements_raspberry_pi.txt"
    
    # Install with timeout for long compilations
    pip install -r requirements_raspberry_pi.txt --timeout 1000
    
    print_status "Python packages installed"
else
    print_error "requirements_raspberry_pi.txt not found!"
    exit 1
fi

# ============================================================
# 6. Configure User Permissions
# ============================================================
echo ""
echo "Step 6: Configuring user permissions..."

# Add user to required groups
sudo usermod -a -G video $USER
sudo usermod -a -G gpio $USER
sudo usermod -a -G dialout $USER

print_status "User added to video, gpio, and dialout groups"
print_warning "You need to LOGOUT and LOGIN again for group changes to take effect!"

# ============================================================
# 7. Enable UART (for CameraTest.py)
# ============================================================
echo ""
echo "Step 7: Configuring UART..."

# Check if UART is already enabled
if grep -q "enable_uart=1" /boot/config.txt 2>/dev/null || grep -q "enable_uart=1" /boot/firmware/config.txt 2>/dev/null; then
    print_status "UART already enabled"
else
    print_warning "UART needs to be enabled manually:"
    echo "  1. Edit /boot/config.txt (or /boot/firmware/config.txt)"
    echo "  2. Add these lines:"
    echo "       enable_uart=1"
    echo "       dtoverlay=disable-bt"
    echo "  3. Run: sudo systemctl disable hciuart"
    echo "  4. Reboot: sudo reboot"
fi

# ============================================================
# 8. Verify Installation
# ============================================================
echo ""
echo "Step 8: Verifying installation..."

python3 -c "import cv2; print('OpenCV:', cv2.__version__)" && print_status "OpenCV working"
python3 -c "import numpy; print('NumPy:', numpy.__version__)" && print_status "NumPy working"
python3 -c "import serial; print('PySerial:', serial.VERSION)" && print_status "PySerial working"
python3 -c "import yaml; print('PyYAML: OK')" && print_status "PyYAML working"
python3 -c "from PySide6 import QtCore; print('PySide6:', QtCore.__version__)" && print_status "PySide6 working"

# Try picamera2 (may not be in venv)
if python3 -c "from picamera2 import Picamera2" 2>/dev/null; then
    print_status "picamera2 working"
else
    print_warning "picamera2 not accessible (install if you have Pi Camera)"
fi

# ============================================================
# 9. Summary
# ============================================================
echo ""
echo "============================================================"
echo "Setup Complete!"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. IMPORTANT: Logout and login again for permissions!"
echo ""
echo "  3. Test your scripts:"
echo "     python CameraTest.py"
echo "     python pi_pendulum_angle.py"
echo ""
echo "  4. For real-time kernel features, reboot after enabling UART"
echo ""
print_status "All done! Happy coding!"
echo ""

