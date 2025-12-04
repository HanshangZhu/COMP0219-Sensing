import cv2
import numpy as np
import time

class PendulumAngleEstimator:
    def __init__(self, camera_index=0):
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise ValueError("Could not open webcam.")
            
        # Default Range (Green-ish)
        self.lower_color = np.array([35, 50, 50])
        self.upper_color = np.array([85, 255, 255])
        
        self.prev_theta = 0.0
        self.alpha = 0.2 
        
        cv2.namedWindow("Pendulum Tracker")
        cv2.setMouseCallback("Pendulum Tracker", self.mouse_callback)
        self.current_frame = None

    def mouse_callback(self, event, x, y, flags, param):
        """Left Click: Pick the color of BOTH pins at once"""
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.current_frame is None: return
            
            hsv = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2HSV)
            pixel = hsv[y, x]
            h, s, v = pixel
            
            # Wide range to catch both pins
            self.lower_color = np.array([max(0, h-20), max(30, s-60), max(30, v-60)])
            self.upper_color = np.array([min(179, h+20), min(255, s+60), min(255, v+60)])
            print(f"Color set to: {pixel}")

    def run(self):
        print("--- PENDULUM ANGLE TRACKER (SAME COLOR MODE) ---")
        print("1. Click on ONE of the green pins to set color.")
        print("2. The script will find the TWO largest green blobs.")
        print("3. Top blob = Pivot, Bottom blob = Bob.")
        
        while True:
            ret, frame = self.cap.read()
            if not ret: break
            self.current_frame = frame
            
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
                # We found at least 2 objects!
                for c in blobs:
                    if cv2.contourArea(c) < 50: continue # Ignore tiny noise
                    
                    M = cv2.moments(c)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        points.append((cx, cy))
                
                if len(points) == 2:
                    # Sort by Y coordinate (Height)
                    # Smallest Y is at the top (Pivot), Largest Y is at the bottom (Bob)
                    points.sort(key=lambda p: p[1]) 
                    
                    top_pt = points[0] # Pivot
                    bot_pt = points[1] # Bob
                    
                    # Draw
                    cv2.circle(display, top_pt, 8, (255, 0, 0), -1) # Blue = Top
                    cv2.circle(display, bot_pt, 8, (0, 0, 255), -1) # Red = Bottom
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
                    print(text) # Print to terminal
                    cv2.putText(display, text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            
            # Show mask for debugging
            mask_small = cv2.resize(mask, (160, 120))
            display[0:120, 0:160] = cv2.cvtColor(mask_small, cv2.COLOR_GRAY2BGR)
            
            cv2.imshow("Pendulum Tracker", display)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    PendulumAngleEstimator().run()
