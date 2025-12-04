import cv2
import numpy as np
import time
import argparse
import math
import serial

# --- RASPBERRY PI CAMERA SETUP ---
try:
    from picamera2 import Picamera2
    HAS_PI_CAMERA = True
except ImportError:
    print("Warning: picamera2 not found. This script is intended for Raspberry Pi.")
    print("Falling back to cv2.VideoCapture(0) for testing on PC...")
    HAS_PI_CAMERA = False

class PendulumAngleEstimatorPi:
    def __init__(self, output_mode='speed', calibration_constant=1.0, fast_motion=False, 
                 serial_port=None, serial_baud=115200):
        """
        Initialize the pendulum angle estimator.
        
        Args:
            output_mode: 'angle' to print angle, 'speed' to print wind speed (default)
            calibration_constant: C value for wind speed calculation V = C * sqrt(tan(angle))
            fast_motion: Enable optimizations for fast-moving objects (default: False)
            serial_port: Serial port for UART output (e.g., '/dev/ttyAMA0'), None to disable
            serial_baud: Serial baud rate (default: 115200)
        """
        # Store fast motion mode
        self.fast_motion = fast_motion
        
        # Initialize Serial/UART (optional)
        self.serial_port = None
        if serial_port:
            try:
                self.serial_port = serial.Serial(
                    port=serial_port,
                    baudrate=serial_baud,
                    timeout=1,
                    write_timeout=2
                )
                print(f"Serial UART initialized: {serial_port} @ {serial_baud} baud")
            except Exception as e:
                print(f"Warning: Could not open serial port {serial_port}: {e}")
                print("Continuing without serial output...")
                self.serial_port = None
        
        # Initialize Camera
        if HAS_PI_CAMERA:
            self.picam2 = Picamera2()
            # Configure for 640x480 @ 30fps for good performance
            config = self.picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)})
            self.picam2.configure(config)
            self.picam2.start()
            print("PiCamera2 started.")
        else:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise ValueError("Could not open webcam.")

        # Default color range (Green-ish) - can be changed by clicking
        # Default Target: [100, 104, 149]
        # For fast motion: slightly wider tolerance and less filtering
        if fast_motion:
            self.hue_tolerance = 25      # ±25 instead of ±20 (moderate increase)
            self.sat_tolerance = 70      # ±70 instead of ±60 (moderate increase)
            self.val_tolerance = 70      # ±70 instead of ±60 (moderate increase)
            self.min_area = 30           # Lower threshold (was 50, not too low)
            self.erode_iterations = 0    # Skip erosion to preserve blurred objects
            self.dilate_iterations = 2   # Same as normal
        else:
            self.hue_tolerance = 20
            self.sat_tolerance = 60
            self.val_tolerance = 60
            self.min_area = 50
            self.erode_iterations = 1
            self.dilate_iterations = 2
        
        h, s, v = 100, 104, 149
        self.lower_color = np.array([max(0, h-self.hue_tolerance), 
                                     max(30, s-self.sat_tolerance), 
                                     max(30, v-self.val_tolerance)], dtype=np.uint8)
        self.upper_color = np.array([min(179, h+self.hue_tolerance), 
                                     min(255, s+self.sat_tolerance), 
                                     min(255, v+self.val_tolerance)], dtype=np.uint8)
        
        print(f"Default Tracking Color: HSV[{h}, {s}, {v}]")
        print(f"Default Range: {self.lower_color} to {self.upper_color}")

        self.prev_theta = 0.0
        self.alpha = 0.2  # Smoothing factor for angle filtering
        
        # Output mode and calibration constant
        self.output_mode = output_mode  # 'angle' or 'speed'
        self.calibration_constant = calibration_constant  # C in formula V = C * sqrt(tan(angle))
        
        # Store current frame for mouse callback
        self.current_frame = None
        
        # On Pi, we might not have a display, so we print to terminal mostly
        # But we'll keep imshow for VNC/Desktop preview
        self.window_name = "Pi Pendulum Tracker"
        
        # Set up mouse callback for color picking
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

    def mouse_callback(self, event, x, y, flags, param):
        """Left Click: Pick the color at the clicked position for tracking"""
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.current_frame is None:
                return
            
            try:
                # Convert the clicked point to HSV and extract color
                hsv = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2HSV)
                pixel = hsv[y, x]
                h, s, v = int(pixel[0]), int(pixel[1]), int(pixel[2])  # Explicitly convert to int
                
                # Create a range using current tolerance settings
                # Explicitly cast to uint8 to match OpenCV's expected type
                self.lower_color = np.array([max(0, h-self.hue_tolerance), 
                                            max(30, s-self.sat_tolerance), 
                                            max(30, v-self.val_tolerance)], dtype=np.uint8)
                self.upper_color = np.array([min(179, h+self.hue_tolerance), 
                                            min(255, s+self.sat_tolerance), 
                                            min(255, v+self.val_tolerance)], dtype=np.uint8)
                
                # Print the selected color for debugging
                print(f"Color picked at ({x}, {y}): HSV[{h}, {s}, {v}]")
                print(f"New Range: {self.lower_color} to {self.upper_color}")
            except Exception as e:
                print(f"Error in mouse callback: {e}")

    def get_frame(self):
        if HAS_PI_CAMERA:
            # capture_array returns RGB, OpenCV uses BGR
            frame_rgb = self.picam2.capture_array()
            return cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        else:
            ret, frame = self.cap.read()
            return frame if ret else None

    def send_serial(self, value):
        """
        Send data over serial UART port
        
        Args:
            value: Float value to send (angle or wind speed)
        """
        if self.serial_port is None:
            return
        
        try:
            # Format message similar to CameraTest.py
            message = f"{value:.1f}\r\n"
            self.serial_port.write(message.encode("utf-8"))
            self.serial_port.flush()  # Ensure all bytes are transmitted
        except serial.SerialTimeoutException:
            print("⚠️ Serial write timeout — the UART buffer may be full.")
        except Exception as e:
            print(f"Serial write error: {e}")
    
    def calculate_wind_speed(self, angle_deg):
        """
        Calculate wind speed from pendulum angle using V = C * sqrt(tan(angle))
        
        Args:
            angle_deg: Pendulum angle in degrees
            
        Returns:
            Wind speed in m/s, or 0 if calculation is invalid
        """
        try:
            # Convert angle to radians
            angle_rad = math.radians(abs(angle_deg))
            
            # Avoid division by zero and negative values under sqrt
            if angle_rad < 0.001:  # Angle too small (< ~0.06 degrees)
                return 0.0
            
            # Calculate V = C * sqrt(tan(angle))
            tan_angle = math.tan(angle_rad)
            
            if tan_angle < 0:
                return 0.0
            
            wind_speed = self.calibration_constant * math.sqrt(tan_angle)
            return wind_speed
            
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    def run(self):
        print("--- RASPBERRY PI PENDULUM TRACKER (INTERACTIVE MODE) ---")
        print("Instructions:")
        print("1. LEFT CLICK on one of the colored pins to set tracking color.")
        print("2. The script will find the TWO largest matching blobs.")
        print("3. Top blob = Pivot, Bottom blob = Bob.")
        print("4. Press 'q' to quit.")
        print(f"Output Mode: {'ANGLE' if self.output_mode == 'angle' else 'WIND SPEED'}")
        if self.output_mode == 'speed':
            print(f"Calibration Constant C: {self.calibration_constant}")
        if self.fast_motion:
            print(f"Fast Motion Mode: ON (Hue±{self.hue_tolerance}, MinArea={self.min_area})")
        if self.serial_port is not None:
            print(f"Serial Output: ENABLED (Port: {self.serial_port.port}, Baud: {self.serial_port.baudrate})")
        else:
            print("Serial Output: DISABLED")
        print()
        
        while True:
            frame = self.get_frame()
            if frame is None: break
            
            # Store frame for mouse callback
            self.current_frame = frame
            
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, self.lower_color, self.upper_color)
            
            # Clean noise (adjust based on fast_motion mode)
            kernel = np.ones((3,3), np.uint8)
            if self.erode_iterations > 0:
                mask = cv2.erode(mask, kernel, iterations=self.erode_iterations)
            if self.dilate_iterations > 0:
                mask = cv2.dilate(mask, kernel, iterations=self.dilate_iterations)
            
            # Find ALL contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Sort by area (largest first) and keep top 2
            blobs = sorted(contours, key=cv2.contourArea, reverse=True)[:2]
            
            display = frame.copy()
            
            points = []
            if len(blobs) >= 2:
                for c in blobs:
                    if cv2.contourArea(c) < self.min_area: continue  # Use dynamic threshold
                    
                    M = cv2.moments(c)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        points.append((cx, cy))
                
                if len(points) == 2:
                    # Sort by Y coordinate (Height)
                    points.sort(key=lambda p: p[1]) 
                    
                    top_pt = points[0] # Pivot
                    bot_pt = points[1] # Bob
                    
                    # Draw
                    cv2.circle(display, top_pt, 8, (255, 0, 0), -1)
                    cv2.circle(display, bot_pt, 8, (0, 0, 255), -1)
                    cv2.line(display, top_pt, bot_pt, (0, 255, 0), 2)
                    
                    # Calculate Angle
                    dx = bot_pt[0] - top_pt[0]
                    dy = bot_pt[1] - top_pt[1]
                    
                    theta_rad = np.arctan2(dx, dy)
                    theta_deg = np.degrees(theta_rad)
                    
                    # Smooth
                    theta_smooth = (self.alpha * theta_deg) + ((1 - self.alpha) * self.prev_theta)
                    self.prev_theta = theta_smooth
                    
                    # Output based on mode
                    if self.output_mode == 'angle':
                        # Print angle in format: angle:xx.x
                        print(f"angle:{theta_smooth:.1f}")
                        display_text = f"Angle: {theta_smooth:.1f} deg"
                        # Send angle over serial
                        self.send_serial(theta_smooth)
                    else:
                        # Calculate and print wind speed (just the number)
                        wind_speed = self.calculate_wind_speed(theta_smooth)
                        print(f"{wind_speed:.1f}")
                        display_text = f"Speed: {wind_speed:.1f} m/s (Angle: {theta_smooth:.1f})"
                        # Send wind speed over serial
                        self.send_serial(wind_speed)
                    
                    # Display on screen
                    cv2.putText(display, display_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # Show mask preview in corner for debugging (optional but helpful)
            mask_small = cv2.resize(mask, (160, 120))
            display[0:120, 0:160] = cv2.cvtColor(mask_small, cv2.COLOR_GRAY2BGR)
            
            # Add instruction text at bottom
            cv2.putText(display, "Left-click to pick color", (20, display.shape[0] - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Show
            cv2.imshow(self.window_name, display)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        if HAS_PI_CAMERA:
            self.picam2.stop()
        else:
            self.cap.release()
        
        # Close serial port if open
        if self.serial_port is not None:
            try:
                self.serial_port.close()
                print("\nSerial port closed.")
            except Exception as e:
                print(f"Error closing serial port: {e}")
        
        cv2.destroyAllWindows()

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Pendulum Angle Tracker with Wind Speed Estimation and UART Output')
    parser.add_argument('--angle', action='store_true', 
                       help='Output angle instead of wind speed (format: angle:xx.x)')
    parser.add_argument('-C', '--calibration', type=float, default=1.0,
                       help='Calibration constant C for wind speed formula V = C * sqrt(tan(angle)) (default: 1.0)')
    parser.add_argument('--fast', action='store_true',
                       help='Enable fast motion mode (wider color tolerance, reduced blur, lower thresholds)')
    parser.add_argument('--serial', type=str, default=None,
                       help='Serial port for UART output (e.g., /dev/ttyAMA0). Disabled by default.')
    parser.add_argument('--baud', type=int, default=115200,
                       help='Serial baud rate (default: 115200)')
    
    args = parser.parse_args()
    
    # Determine output mode
    output_mode = 'angle' if args.angle else 'speed'
    
    # Create and run the estimator
    estimator = PendulumAngleEstimatorPi(output_mode=output_mode, 
                                         calibration_constant=args.calibration,
                                         fast_motion=args.fast,
                                         serial_port=args.serial,
                                         serial_baud=args.baud)
    estimator.run()

