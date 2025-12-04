#!/usr/bin/env python3
"""
Debug version of live plotter - Single device only
Reads from one serial port and displays real-time graph
"""
import sys, time, collections, os, csv
from PySide6 import QtCore, QtWidgets
import pyqtgraph as pg
import serial, serial.tools.list_ports
try:
    import yaml
except ImportError:
    yaml = None

class SerialReader(QtCore.QThread):
    """Thread to read from serial port"""
    data_received = QtCore.Signal(str, float, float)  # port, timestamp, value
    disconnected = QtCore.Signal(str)  # port

    def __init__(self, port_name: str, baud: int = 115200, parent=None):
        super().__init__(parent)
        self._port_name = port_name
        self._baud = baud
        self._stop = False
        self._last_data_ts = 0.0

    def run(self):
        """Main loop: read serial data"""
        try:
            ser = serial.Serial(self._port_name, self._baud, timeout=1)
        except Exception as e:
            print(f"Failed to open {self._port_name}: {e}")
            self.disconnected.emit(self._port_name)
            return
        
        with ser:
            while not self._stop:
                try:
                    line = ser.readline().decode(errors="ignore").strip()
                    if not line:
                        continue
                    
                    # Parse value (expect just a number)
                    value = float(line)
                    ts = time.time()
                    self.data_received.emit(self._port_name, ts, value)
                    self._last_data_ts = ts
                    
                except ValueError:
                    continue  # Skip invalid lines
                except Exception as e:
                    print(f"Read error on {self._port_name}: {e}")
                    break
        
        self.disconnected.emit(self._port_name)

    def stop(self):
        """Stop the reader thread"""
        self._stop = True
        self.wait(500)


class DebugWindow(QtWidgets.QMainWindow):
    """Simple single-device live plotter"""
    
    def __init__(self, port, name, baud=115200, max_points=3000, 
                 refresh_ms=30, window_seconds=15, max_speed=10.0, min_speed=0.0):
        super().__init__()
        self.setWindowTitle(f"Debug Plotter - {name}")
        self.resize(900, 500)
        
        # Store parameters
        self.port = port
        self.name = name
        self.max_points = max_points
        self.window_seconds = float(window_seconds)
        self.max_speed = float(max_speed)
        self.min_speed = float(min_speed)
        
        # Data buffers
        self.t_buffer = collections.deque(maxlen=self.max_points)
        self.v_buffer = collections.deque(maxlen=self.max_points)
        self.t0 = time.time()
        
        # Logging state
        self.logging_active = False
        self.log_rows = []
        
        # Setup UI
        self._setup_ui()
        
        # Start serial reader
        self.reader = SerialReader(port, baud=baud)
        self.reader.data_received.connect(self.on_data)
        self.reader.disconnected.connect(self.on_disconnected)
        self.reader.start()
        
        # Refresh timer
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(int(refresh_ms))

    def _setup_ui(self):
        """Create UI layout"""
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)
        
        # Controls: logging toggle
        controls = QtWidgets.QWidget()
        controls_layout = QtWidgets.QHBoxLayout(controls)
        controls_layout.setContentsMargins(8, 8, 8, 0)
        self.btn_log = QtWidgets.QPushButton("Start Logging")
        self.btn_log.clicked.connect(self.toggle_logging)
        self.lbl_log_status = QtWidgets.QLabel("Logging: OFF")
        self.lbl_log_status.setStyleSheet("color: #666;")
        controls_layout.addWidget(self.btn_log)
        controls_layout.addWidget(self.lbl_log_status)
        controls_layout.addStretch(1)
        main_layout.addWidget(controls)
        
        # Header: large numeric display
        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QVBoxLayout(header)
        header_layout.setContentsMargins(8, 8, 8, 8)
        title_label = QtWidgets.QLabel(f"{self.name} ({self.port})")
        title_label.setStyleSheet("color: #666; font-size: 12pt;")
        self.value_label = QtWidgets.QLabel("—")
        self.value_label.setStyleSheet("font-size: 36pt; font-weight: 600; color: #0a0;")
        header_layout.addWidget(title_label)
        header_layout.addWidget(self.value_label)
        main_layout.addWidget(header)
        
        # Plot
        self.plot = pg.PlotWidget()
        main_layout.addWidget(self.plot, 1)
        self.plot.addLegend()
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setLabel('left', 'Value', units='m/s')
        self.plot.setLabel('bottom', 'Time', units='s')
        self.plot.getViewBox().enableAutoRange(x=False, y=False)
        
        # Create curve
        self.curve = self.plot.plot(pen=pg.mkPen('g', width=2), name=self.name)
        
        # Set initial Y range
        self.plot.setYRange(self.min_speed, self.max_speed, padding=0)

    @QtCore.Slot(str, float, float)
    def on_data(self, port, ts, value):
        """Handle incoming data"""
        t_rel = ts - self.t0
        
        # Clip value to range
        clipped = max(self.min_speed, min(self.max_speed, value))
        
        # Add to buffers
        self.t_buffer.append(t_rel)
        self.v_buffer.append(clipped)
        
        # Update numeric display
        self.value_label.setText(f"{clipped:.3f} m/s")
        
        # Logging
        if self.logging_active:
            iso = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(ts)) + f".{int((ts%1)*1000):03d}Z"
            row = [iso, f"{ts:.6f}", f"{t_rel:.6f}", f"{value:.6f}", f"{clipped:.6f}"]
            self.log_rows.append(row)

    @QtCore.Slot(str)
    def on_disconnected(self, port):
        """Handle device disconnection"""
        print(f"Device disconnected: {port}")
        self.value_label.setText("DISCONNECTED")
        self.value_label.setStyleSheet("font-size: 36pt; font-weight: 600; color: #f00;")

    def refresh(self):
        """Update plot"""
        if not self.t_buffer:
            return
        
        # Update curve
        t_list = list(self.t_buffer)
        v_list = list(self.v_buffer)
        self.curve.setData(t_list, v_list)
        
        # Set rolling window X range
        latest_ts = t_list[-1]
        start = max(0.0, latest_ts - self.window_seconds)
        self.plot.setXRange(start, latest_ts, padding=0)
        
        # Dynamic Y range (fit to visible data)
        if latest_ts > 0:
            t_cut = latest_ts - self.window_seconds
            visible_values = [v for t, v in zip(t_list, v_list) if t >= t_cut]
            if visible_values:
                v_max = max(visible_values)
                v_min = min(visible_values)
                # Add 10% padding
                padding = (v_max - v_min) * 0.1
                self.plot.setYRange(v_min - padding, v_max + padding, padding=0)

    def toggle_logging(self):
        """Start/stop logging"""
        if not self.logging_active:
            # Start logging
            self.logging_active = True
            self.log_rows = []
            self.btn_log.setText("Stop & Save")
            self.lbl_log_status.setText("Logging: ON")
            self.lbl_log_status.setStyleSheet("color: #0a0;")
        else:
            # Stop logging and save
            self.logging_active = False
            self.btn_log.setText("Start Logging")
            self.lbl_log_status.setText("Logging: OFF")
            self.lbl_log_status.setStyleSheet("color: #666;")
            
            if not self.log_rows:
                return
            
            # Save dialog
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save CSV", "", "CSV Files (*.csv)")
            if not path:
                return
            if not path.lower().endswith('.csv'):
                path += '.csv'
            
            # Write CSV
            try:
                with open(path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['timestamp_iso', 'timestamp_epoch', 't_rel_s', 'value_raw', 'value_clipped'])
                    writer.writerows(self.log_rows)
                print(f"Saved log to {path} ({len(self.log_rows)} rows)")
            except Exception as e:
                print(f"Error saving CSV: {e}")

    def closeEvent(self, event):
        """Clean shutdown"""
        self.reader.stop()
        super().closeEvent(event)


def list_ports():
    """List available serial ports"""
    print("Available serial ports:")
    for p in serial.tools.list_ports.comports():
        print(f"  {p.device}: {p.description}")


def main():
    """Main entry point"""
    if yaml is None:
        print("PyYAML is required. Install with: pip install pyyaml")
        sys.exit(1)
    
    # Load config
    config_path = os.path.join(os.path.dirname(__file__), "debug_config.yaml")
    if not os.path.exists(config_path):
        print(f"Config not found: {config_path}")
        list_ports()
        sys.exit(1)
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Failed to read debug_config.yaml: {e}")
        sys.exit(1)
    
    # Parse device
    devices = config.get("devices", [])
    if not devices or len(devices) != 1:
        print("ERROR: debug_config.yaml must have exactly ONE device configured.")
        print("Example:")
        print("devices:")
        print("  - name: Test Device")
        print("    port: COM3")
        print("    baud: 115200")
        list_ports()
        sys.exit(1)
    
    device = devices[0]
    port = device.get('port')
    name = device.get('name', 'Device')
    baud = int(device.get('baud', 115200))
    
    if not port:
        print("ERROR: Device is missing 'port' in debug_config.yaml")
        sys.exit(1)
    
    print(f"Starting debug plotter for: {name} @ {port} ({baud} baud)")
    
    # Parse UI config
    ui_cfg = config.get("ui", {}) or {}
    max_points = int(ui_cfg.get("max_points", 3000))
    refresh_ms = int(ui_cfg.get("refresh_ms", 30))
    window_seconds = float(ui_cfg.get("window_seconds", 15))
    max_speed = float(ui_cfg.get("max_speed", 10))
    min_speed = float(ui_cfg.get("min_speed", 0))
    
    # Start app
    app = QtWidgets.QApplication(sys.argv)
    window = DebugWindow(
        port=port,
        name=name,
        baud=baud,
        max_points=max_points,
        refresh_ms=refresh_ms,
        window_seconds=window_seconds,
        max_speed=max_speed,
        min_speed=min_speed
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

