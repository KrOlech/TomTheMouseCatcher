import cv2
import numpy as np

# ===== SETTINGS =====
marker_id = 23
dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

# high-resolution image for printing
marker_pixels = 1200   # large source image -> sharp print
marker = cv2.aruco.generateImageMarker(dictionary, marker_id, marker_pixels)

# Create white page around marker
# final canvas proportion ~ 30 x 45 mm = 2:3
canvas_h = 1800
canvas_w = 1200
canvas = np.ones((canvas_h, canvas_w), dtype=np.uint8) * 255

# Put square marker near top-center
top_margin = 120
left = (canvas_w - marker_pixels) // 2
canvas[top_margin:top_margin + marker_pixels, left:left + marker_pixels] = marker

# Optional text below marker
cv2.putText(
    canvas,
    "ArUco ID 23",
    (260, 1500),
    cv2.FONT_HERSHEY_SIMPLEX,
    2.0,
    0,
    4,
    cv2.LINE_AA
)

cv2.imwrite("aruco_id23_print.png", canvas)
print("Saved: aruco_id23_print.png")