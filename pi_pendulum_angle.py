import cv2
import numpy as np
import time

# --- RASPBERRY PI CAMERA SETUP ---
try:
    from picamera2 import Picamera2
    HAS_PI_CAMERA = True
except ImportError:
    print("Warning: picamera2 not found. This script is intended for Raspberry Pi.")
    print("Falling back to cv2.VideoCapture(0) for testing on PC...")
    HAS_PI_CAMERA = False

class PendulumAngleEstimatorPi:
    def __init__(self):
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

        # HARDCODED RANGE from User
        # Target: [100, 104, 149]
        # Range:  +/- 20 Hue, +/- 60 Sat/Val
        h, s, v = 100, 104, 149
        self.lower_color = np.array([max(0, h-20), max(30, s-60), max(30, v-60)])
        self.upper_color = np.array([min(179, h+20), min(255, s+60), min(255, v+60)])
        
        print(f"Tracking Color: HSV[{h}, {s}, {v}]")
        print(f"Range: {self.lower_color} to {self.upper_color}")

        self.prev_theta = 0.0
        self.alpha = 0.2 
        
        # On Pi, we might not have a display, so we print to terminal mostly
        # But we'll keep imshow for VNC/Desktop preview
        self.window_name = "Pi Pendulum Tracker"

    def get_frame(self):
        if HAS_PI_CAMERA:
            # capture_array returns RGB, OpenCV uses BGR
            frame_rgb = self.picam2.capture_array()
            return cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        else:
            ret, frame = self.cap.read()
            return frame if ret else None

    def run(self):
        print("--- RASPBERRY PI PENDULUM TRACKER ---")
        print("Using hardcoded color. Press 'q' to quit.")
        
        while True:
            frame = self.get_frame()
            if frame is None: break
            
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, self.lower_color, self.upper_color)
            
            # Clean noise
            kernel = np.ones((3,3), np.uint8)
            mask = cv2.erode(mask, kernel, iterations=1)
            mask = cv2.dilate(mask, kernel, iterations=2)
            
            # Find ALL contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Sort by area (largest first) and keep top 2
            blobs = sorted(contours, key=cv2.contourArea, reverse=True)[:2]
            
            display = frame.copy()
            
            points = []
            if len(blobs) >= 2:
                for c in blobs:
                    if cv2.contourArea(c) < 50: continue
                    
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
                    
                    # Output
                    text = f"Angle: {theta_smooth:.2f}"
                    print(text) # Print to terminal for logging
                    cv2.putText(display, text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            
            # Show
            cv2.imshow(self.window_name, display)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        if HAS_PI_CAMERA:
            self.picam2.stop()
        else:
            self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    PendulumAngleEstimatorPi().run()

