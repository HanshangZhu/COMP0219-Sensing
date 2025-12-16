# Comprehensive Guide: Raspberry Pi Pendulum Wind Speed Sensor

## 1. Project Overview
This project implements a **computer vision-based wind speed sensor** using a Raspberry Pi and a simple pendulum. By tracking the angle of a pendulum equipped with colored markers, the system calculates wind speed using the physical relationship:

$$ V = C \cdot \sqrt{\tan(\theta)} $$

Where:
*   **V**: Wind speed (m/s)
*   **C**: Calibration constant (derived experimentally)
*   **θ**: Pendulum angle (degrees)

The system is designed to process video in real-time, calculate the wind speed, and transmit the data via UART to an external controller (e.g., STM32) or display it locally.

## 2. System Architecture

The full system consists of three main stages:

1.  **Sensing Node (Raspberry Pi 4)**
    *   **Input**: Camera feed (Pi Camera Module).
    *   **Processing**: `pi_pendulum_angle.py` tracks the pendulum markers (pivot & bob), calculates the angle, and computes wind speed.
    *   **Output**: Sends wind speed (or angle) via UART (`/dev/ttyAMA0`).

2.  **Bridge/Controller (STM32)**
    *   **Role**: Receives UART data from the Pi.
    *   **Firmware**: Located in `STM32_UART_Bridge_project`.
    *   **Function**: Acts as a bridge to forward data to a PC or perform embedded control tasks.

3.  **Visualization (PC)**
    *   **Software**: Python/Qt GUI located in `LiveGraphing` or `Updated_GUI_Rev3`.
    *   **Function**: Plots real-time wind speed data received from the STM32 (via USB/UART).

## 3. Hardware Requirements

*   **Raspberry Pi**: Model 4 recommended (3B+ compatible).
*   **Camera**: Pi Camera Module v2, v3, or HQ Camera.
*   **Pendulum**: A lightweight rod/string with two distinct colored markers (one at the pivot, one at the bottom bob).
*   **STM32 Nucleo Board** (Optional, for bridging): For receiving UART data.
*   **Wiring**:
    *   Ti UART TX (GPIO 14) -> STM32 RX.
    *   Pi UART RX (GPIO 15) -> STM32 TX.
    *   GND -> GND.

## 4. Raspberry Pi Setup

### 4.1. OS & Prerequisites
Ensure your Raspberry Pi is running Raspberry Pi OS (Bullseye or Bookworm).

1.  **Enable Camera & UART**:
    ```bash
    sudo raspi-config
    # Interface Options -> Camera (Enable)
    # Interface Options -> Serial Port (Enable Serial Hardware, Disable Console)
    ```

2.  **Install Dependencies**:
    The repository includes a setup script to automate installation.
    ```bash
    cd comp0219_cw2
    chmod +x setup_raspberry_pi.sh
    ./setup_raspberry_pi.sh
    ```
    *This script installs OpenCV, NumPy, Picamera2, and configures permissions.*

### 4.2. Camera Calibration (Week 7)
If you need to calibrate the camera lens itself (undistortion), refer to `Week_7_Calibration_Tutorial`. However, for the pendulum tracker, standard lens distortion is often negligible unless you are using a fisheye lens.

## 5. Usage Guide

### 5.1. Sensor Calibration
Before using the sensor, you must find the constant **C**.

1.  **Run Calibration Tool**:
    ```bash
    python calibrate_pendulum.py
    ```
2.  **Procedure**:
    *   Expose the pendulum to known wind speeds (e.g., using a reference anemometer).
    *   Enter the measured angle (from the tool) and the reference wind speed.
    *   Repeat for 5-10 data points.
3.  **Result**:
    *   The tool saves `pendulum_calibration.json`. The main tracker will automatically load this file.

### 5.2. Running the Tracker
To start the wind speed sensor:

```bash
python pi_pendulum_angle.py
```

*   **Interactive Setup**:
    *   A window will appear showing the camera feed.
    *   **Left-Click** on the colored marker (bob/pivot) to tell the computer vision algorithm which color to track.
    *   The system identifies the two largest blobs of that color (Pivot = Top, Bob = Bottom).

*   **Command Line Options**:
    *   `--angle`: Output raw angle instead of calculated wind speed.
    *   `--fast`: Enable optimization for fast-moving markers (wider color tolerance).
    *   `--serial /dev/ttyAMA0`: Specify UART port (Default: `/dev/ttyAMA0`).
    *   `-C 1.5`: Manually override calibration constant.

### 5.3. Monitoring Data on PC
To view the data on a Windows/Mac PC:

1.  Connect the STM32 (bridging the Pi data) to your PC via USB.
2.  Navigate to `LiveGraphing`:
    ```bash
    cd LiveGraphing
    pip install -r requirements.txt  # If needed (PySide6, pyqtgraph)
    ```
3.  Run the visualizer:
    ```bash
    python Testing_Windows.py
    ```
    *Ensure `config.yaml` or the script points to the correct COM port.*

## 6. Directory Structure

*   **/ (Root)**: Main Pi scripts (`pi_pendulum_angle.py`, `calibrate_pendulum.py`).
*   **STM32_UART_Bridge_project/**: CubeIDE project for the STM32 firmware.
*   **LiveGraphing/**: PC-side Python GUI for plotting live data.
*   **Updated_GUI_Rev3/**: Alternative/Legacy GUI version.
*   **Week_X_Tutorials/**: Educational material and isolated test scripts for specific CV tasks (Calibration, Segmentation, Line Fitting).

## 7. Troubleshooting

*   **"Picamera2 not found"**: Ensure you are running on a Raspberry Pi. On a PC, the script attempts to fall back to a webcam (`cv2.VideoCapture`).
*   **"Serial Permission Denied"**: Add your user to the dialout group:
    ```bash
    sudo usermod -a -G dialout $USER
    ```
    Then logout and login.
*   **Tracking Jitter**:
    *   Ensure lighting is consistent.
    *   Use distinct colors for markers (e.g., bright pink or green) that don't exist in the background.
    *   Try `--fast` mode if the pendulum swings violently.
