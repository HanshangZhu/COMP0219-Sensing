"""
Minimal Color Segmentation Example
The simplest possible implementation - just the core concept!
"""

import cv2
import numpy as np

# Open video
############for pi_camera : ###############
# from picamera2 import Picamera2
# picam2 = Picamera2()
# config = picam2.create_preview_configuration(main={"format": "RGB888", "size": (1280, 720)})
# picam2.configure(config)
# picam2.start()
###########################################
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
############for pi_camera : ###############
# frame = picam2.capture_array()
# ret = True
###########################################

# Convert to HSV and pick a color at position (300, 300)
hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
h, s, v = hsv[300, 300]  # Pick color at this position

# Create color range (±10 hue, ±60 saturation/value)
# Use max/min to cap values within valid HSV range
lower = np.array([max(0, int(h)-10), max(0, int(s)-60), max(0, int(v)-60)], dtype=np.uint8)
upper = np.array([min(179, int(h)+10), min(255, int(s)+60), min(255, int(v)+60)], dtype=np.uint8)

print(f"Selected HSV: H={h}, S={s}, V={v}")
print(f"Range: {lower} to {upper}")

# Process video
# cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Restart from beginning (Not needed for webcam)

while True:
    ret, frame = cap.read()
    ############for pi_camera : ###############
    # frame = picam2.capture_array()
    # ret = True
    ###########################################
    if not ret:
        break
    
    # Convert to HSV and create mask
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower, upper)
    
    # Apply mask (keep color, black out rest)
    result = cv2.bitwise_and(frame, frame, mask=mask)
    
    # Display side-by-side
    cv2.imshow('Original | Segmented', np.hstack((frame, result)))
    
    if cv2.waitKey(30) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

