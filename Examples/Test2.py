import cv2
import numpy as np
import matplotlib.pyplot as plt
import time

video_path = r"C:\Users\Zenbook\Downloads\m16.avi"
# video_path = r"C:\Users\Zenbook\Downloads\output 2026-01-19 11-12-52.mp4"


V_MAX = 1500

STOP_SPEED = 20       # px/s
STOP_ACCEL = 50       # px/s²
STOP_FRAMES = 5

stop_counter = 0

x_std_meas, y_std_meas = 0.1, 0.1
std_acc = 2

target_fps = 60
frame_delay = 1.0 / target_fps

dt = frame_delay  # time step

# Define the  control input variables acceleration in x and y direction
u = np.matrix([[0], [0]])

# Intial State
x = np.matrix([[0], [500], [0], [0], [0], [0]])

# Define the State Transition Matrix A
A = np.matrix([
    [1, 0, dt, 0, 0.5*dt**2, 0],
    [0, 1, 0, dt, 0, 0.5*dt**2],
    [0, 0, 1, 0, dt, 0],
    [0, 0, 0, 1, 0, dt],
    [0, 0, 0, 0, 0.9, 0],
    [0, 0, 0, 0, 0, 0.9]
])

# Define Measurement Mapping Matrix
H = np.matrix([
    [1, 0, 0, 0, 0, 0],
    [0, 1, 0, 0, 0, 0]])

# Initial Process Noise Covariance
q = std_acc**2

Q = np.matrix([
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, q*dt**2, 0, q*dt, 0],
    [0, 0, 0, q*dt**2, 0, q*dt],
    [0, 0, q*dt, 0, q, 0],
    [0, 0, 0, q*dt, 0, q]
])

# Initial Measurement Noise Covariance
def adaptive_R(x_pred, z, base_R):
    innovation = z - H @ x_pred
    d = np.linalg.norm(innovation)

    scale = 1 + 0.01 *  d   # adaptive gain
    return base_R * scale

R_base = np.matrix([
    [9, 0],
    [0, 9]
])

# Initial Covariance Matrix
P = np.eye(A.shape[1])

px, py = [], []
vx, vy = [], []
ax, ay = [], []
rx, ry = [], []
speed_log = []
accel_log = []
mesurmentX, mesurmentY = [], []


cap = cv2.VideoCapture(video_path)

kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

vx_prev, vy_prev = 0, 0

while True:
    start_time = time.time()
    ret, frame = cap.read()
    if not ret:
        break

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lower = np.array([160, 120, 0])  # 0,120,0
    upper = np.array([255, 255, 115])  # 255, 255, 120

    mask = cv2.inRange(hsv, lower, upper)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    mask_vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

    x = A @ x
    P = A @ P @ A.T + Q

    if len(x[0]) > 1:
        predictedPosx.append(x[0, 0])
        predictedPosY.append(x[0, 1])

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if not (1300 < area < 2500):
            continue

        xm, y, w, h = cv2.boundingRect(cnt)
        aspect = w / h
        if not (0.5 < aspect < 5.0):
            continue

        # Accepted object → draw it
        cv2.rectangle(frame, (xm, y), (xm + w, y + h), (0, 255, 0), 2)
        cv2.rectangle(mask_vis, (xm, y), (xm + w, y + h), (0, 255, 0), 2)

        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            mesurmentX.append(cx)
            mesurmentY.append(cy)
            cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
            cv2.circle(mask_vis, (cx, cy), 4, (0, 0, 255), -1)

            z = np.matrix([[cx], [cy]])

            R = adaptive_R(x, z, R_base)

            S = H @ P @ H.T + R
            K = P @ H.T @ np.linalg.inv(S)

            x = x + K @ (z - H @ x)

            I = np.eye(6)
            P = (I - K @ H) @ P

            a_meas_x = (x[2,0] - vx_prev) / dt
            a_meas_y = (x[3,0] - vy_prev) / dt

            vx_prev, vy_prev = x[2,0] , x[3,0]

            mup = 0.6
            aup = 0.4

            x[4, 0] = mup * x[4, 0] + aup * a_meas_x
            x[5, 0] = mup * x[5, 0] + aup * a_meas_y

            speed = np.hypot(x[2,0], x[3,0])
            accel = np.hypot(x[4, 0], x[5, 0])

            if speed < STOP_SPEED and accel < STOP_ACCEL:
                stop_counter += 1
            else:
                stop_counter = 0

            if stop_counter >= STOP_FRAMES:
                x[2:] = 0

            if speed > 1e-3:
                dir_x = x[2,0] / speed
                dir_y = x[3,0] / speed

                a_parallel = x[4, 0] * dir_x + x[5, 0] * dir_y
                a_perp_x = x[4, 0] - a_parallel * dir_x
                a_perp_y = x[5, 0] - a_parallel * dir_y

                # Strong forward accel, weak sideways accel
                x[4, 0] = a_parallel * dir_x + 0.3 * a_perp_x
                x[5, 0] = a_parallel * dir_y + 0.3 * a_perp_y

            if speed > V_MAX:
                scale = V_MAX / speed
                x[2, 0] *= scale
                x[3, 0] *= scale

            px.append(x[0, 0])
            py.append(x[1, 0])
            vx.append(x[2, 0])
            vy.append(x[3, 0])
            ax.append(x[4, 0])
            ay.append(x[5, 0])

            rx.append(R[0, 0])
            ry.append(R[1, 1])

            speed_log.append(np.hypot(x[2, 0], x[3, 0]))
            accel_log.append(np.hypot(x[4, 0], x[5, 0]))

            cv2.circle(frame, (int(x[0, 0]), int(x[1, 0])), 4, (255, 0, 0), -1)
            cv2.circle(mask_vis, (int(x[0, 0]), int(x[1, 0])), 4, (255, 0, 0), -1)


    cv2.imshow("Frame", frame)
    cv2.imshow("Mask", mask_vis)

    processing_time = time.time() - start_time
    sleep_time = max(0, frame_delay - processing_time)
    time.sleep(sleep_time)

    if cv2.waitKey(30) & 0xFF == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()


plt.figure(figsize=(12,10))

plt.subplot(3,2,1)
plt.title("Position")
plt.plot(px, label="x")
plt.plot(py, label="y")
plt.legend()

plt.subplot(3,2,2)
plt.title("Velocity")
plt.plot(vx, label="vx")
plt.plot(vy, label="vy")
plt.plot(speed_log, label="speed")
plt.legend()

plt.subplot(3,2,3)
plt.title("Acceleration")
plt.plot(ax, label="ax")
plt.plot(ay, label="ay")
plt.plot(accel_log, label="aXY")
plt.legend()

plt.subplot(3,2,4)
plt.title("Adaptive R")
plt.plot(rx, label="R_x")
plt.plot(ry, label="R_y")
plt.legend()

plt.subplot(3,2,5)
plt.title("Trajectory")
plt.plot(px, py, label="Kalman")
plt.plot(mesurmentX, mesurmentY, '.', alpha=0.3, label="Measurement")
plt.legend()


plt.tight_layout()
plt.show()