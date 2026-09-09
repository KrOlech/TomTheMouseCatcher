import cv2

# ============================================================
# SETTINGS
# ============================================================

input_video = r"C:\Users\kradwanska\Documents\TOM\data\video20260722_17_55_36.avi"
output_video = r"C:\Users\kradwanska\Documents\TOM\data\video20260722_17_55_36_trimmed.avi"

trim_seconds = 15

# ============================================================
# OPEN VIDEO
# ============================================================

cap = cv2.VideoCapture(input_video)

if not cap.isOpened():
    raise RuntimeError("Could not open input video.")

fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

frame_to_start = int(trim_seconds * fps)

print(f"FPS: {fps:.2f}")
print(f"Skipping first {frame_to_start} frames.")

fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter(output_video, fourcc, fps/1.3, (width, height))

# ============================================================
# SKIP FIRST 15 SECONDS
# ============================================================

cap.set(cv2.CAP_PROP_POS_FRAMES, frame_to_start)

written = 0

while True:
    ret, frame = cap.read()

    if not ret:
        break

    out.write(frame)
    written += 1

cap.release()
out.release()

print(f"Done!")
print(f"Frames written: {written}")
print(f"Saved to:\n{output_video}")