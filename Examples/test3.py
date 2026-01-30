import cv2
import numpy as np
import matplotlib.pyplot as plt
import time

#video_path = r"C:\Users\Zenbook\Downloads\m16.avi"
# video_path = r"C:\Users\Zenbook\Downloads\output 2026-01-19 11-12-52.mp4"

video_path = r"C:\Users\Zenbook\Downloads\video20260203_11_00_31.avi"

V_MAX = 1500

STOP_SPEED = 20       # px/s
STOP_ACCEL = 50       # px/s²
STOP_FRAMES = 5

stop_counter = 0

x_std_meas, y_std_meas = 0.1, 0.1
std_acc = 2

target_fps = 10
frame_delay = 1.0 / target_fps

dt = frame_delay  # time step

# Define the  control input variables acceleration in x and y direction
px, py = 0.0, 500.0
vx, vy = 0.0, 0.0

def adaptive_alpha_beta(innovation, speed):
    d = np.linalg.norm(innovation)

    alpha = np.clip(0.4 + 0.01 * d, 0.4, 0.85)
    beta  = np.clip(0.05 + 0.002 * d, 0.05, 0.35)

    return alpha, beta

px_log, py_log = [], []
vx_log, vy_log = [], []
ax_log, ay_log = [], []
rx_log, ry_log = [], []
speed_log = []
accel_log = []
mesurmentX_log, mesurmentY_log = [], []


cap = cv2.VideoCapture(video_path)

cv2.namedWindow("Trackbars")

def nothing(i):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    h_min = cv2.getTrackbarPos("H min", "Trackbars")
    h_max = cv2.getTrackbarPos("H max", "Trackbars")
    s_min = cv2.getTrackbarPos("S min", "Trackbars")
    s_max = cv2.getTrackbarPos("S max", "Trackbars")
    v_min = cv2.getTrackbarPos("V min", "Trackbars")
    v_max = cv2.getTrackbarPos("V max", "Trackbars")

    lower = np.array([h_min, s_min, v_min])
    upper = np.array([h_max, s_max, v_max])  # 255, 255, 120

    mask = cv2.inRange(hsv, lower, upper)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    mask_vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if not (1300 < area < 2500):
            continue

        xm, y, w, h = cv2.boundingRect(cnt)
        aspect = w / h
        if not (0.5 < aspect < 3.3):
            continue

        # Accepted object → draw it

        cv2.rectangle(mask_vis, (xm, y), (xm + w, y + h), (0, 255, 0), 2)
        cv2.putText(mask_vis, str(area) + " " + str(aspect), (xm, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1,
                    cv2.LINE_AA)

    cv2.imshow("Mask", mask_vis)



kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

vx_prev, vy_prev = 0, 0

while True:
    start_time = time.time()
    ret, frame = cap.read()
    if not ret:
        break

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    h_min = cv2.getTrackbarPos("H min", "Trackbars")
    h_max = cv2.getTrackbarPos("H max", "Trackbars")
    s_min = cv2.getTrackbarPos("S min", "Trackbars")
    s_max = cv2.getTrackbarPos("S max", "Trackbars")
    v_min = cv2.getTrackbarPos("V min", "Trackbars")
    v_max = cv2.getTrackbarPos("V max", "Trackbars")

    lower = np.array([h_min, s_min, v_min])
    upper = np.array([h_max, s_max, v_max])  # 255, 255, 120

    mask = cv2.inRange(hsv, lower, upper)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    mask_vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

    px_pred = px + vx * dt
    py_pred = py + vy * dt

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if not (1300 < area < 2500):
            continue

        xm, y, w, h = cv2.boundingRect(cnt)
        aspect = w / h
        if not (0.5 < aspect < 3.3):
            continue

        # Accepted object → draw it
        cv2.rectangle(frame, (xm, y), (xm + w, y + h), (0, 255, 0), 2)
        cv2.rectangle(mask_vis, (xm, y), (xm + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, str(area)+" "+str(aspect), (xm, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1,
                    cv2.LINE_AA)

        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            mesurmentX_log.append(cx)
            mesurmentY_log.append(cy)
            cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
            cv2.circle(mask_vis, (cx, cy), 4, (0, 0, 255), -1)

            # Innovation
            ex = cx - px_pred
            ey = cy - py_pred
            innovation = np.array([ex, ey])

            # Adaptive gains
            alpha, beta = adaptive_alpha_beta(innovation, np.hypot(vx, vy))

            # Update position
            px = px_pred + alpha * ex
            py = py_pred + alpha * ey

            # Update velocity (instant response)
            vx_prev, vy_prev = vx, vy
            vx = vx + (beta / dt) * ex
            vy = vy + (beta / dt) * ey

            ax = (vx - vx_prev) / dt
            ay = (vy - vy_prev) / dt

            speed = np.hypot(vx, vy)
            accel = np.hypot(ax, ay)

            if speed < STOP_SPEED and accel < STOP_ACCEL:
                stop_counter += 1
            else:
                stop_counter = 0

            if stop_counter >= STOP_FRAMES:
                vx = vy = 0.0

            speed = np.hypot(vx, vy)
            if speed > V_MAX:
                scale = V_MAX / speed
                vx *= scale
                vy *= scale

            speed = np.hypot(vx, vy)
            if speed > 1e-3:
                dir_x = vx / speed
                dir_y = vy / speed

                v_parallel = vx * dir_x + vy * dir_y
                vx = v_parallel * dir_x
                vy = v_parallel * dir_y

            px_log.append(px)
            py_log.append(py)
            vx_log.append(vx)
            vy_log.append(vy)
            ax_log.append(ax)
            ay_log.append(ay)
            speed_log.append(speed)
            accel_log.append(accel)

            cv2.circle(frame, (int(px), int(py)), 4, (255, 0, 0), -1)
            cv2.circle(mask_vis, (int(px), int(py)), 4, (255, 0, 0), -1)


    cv2.imshow("Frame", frame)
    cv2.imshow("Mask", mask_vis)

    processing_time = time.time() - start_time
    sleep_time = max(0, frame_delay - processing_time)
    #time.sleep(sleep_time)

    while cv2.waitKey(30) & 0xFF !=  ord('d'):
        ...

    if cv2.waitKey(30) & 0xFF == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()


plt.figure(figsize=(12,10))

plt.subplot(3,2,1)
plt.title("Position")
plt.plot(px_log, label="x")
plt.plot(py_log, label="y")
plt.legend()

plt.subplot(3,2,2)
plt.title("Velocity")
plt.plot(vx_log, label="vx")
plt.plot(vy_log, label="vy")
plt.plot(speed_log, label="speed")
plt.legend()

plt.subplot(3,2,3)
plt.title("Acceleration")
plt.plot(ax_log, label="ax")
plt.plot(ay_log, label="ay")
plt.plot(accel_log, label="aXY")
plt.legend()


plt.subplot(3,2,5)
plt.title("Trajectory")
plt.plot(px_log, py_log, label="Kalman")
plt.plot(mesurmentX_log, mesurmentY_log, '.', alpha=0.3, label="Measurement")
plt.legend()


plt.tight_layout()
plt.show()