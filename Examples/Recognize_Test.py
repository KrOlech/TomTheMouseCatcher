import cv2
import numpy as np
import matplotlib.pyplot as plt

video_path = r"C:\Users\Zenbook\Downloads\m16.avi"
# video_path = r"C:\Users\Zenbook\Downloads\output 2026-01-19 11-12-52.mp4"
cap = cv2.VideoCapture(video_path)

# Morphology kernel
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

x_std_meas, y_std_meas = 5, 5
std_acc = 0.2

dt = 1 / 60  # time step

# Define the  control input variables acceleration in x and y direction
u = np.matrix([[0], [0]])

# Intial State
x = np.matrix([[0, 0], [0, 0], [0, 0], [0, 0]])

# Define the State Transition Matrix A
A = np.matrix([[1, 0, dt, 0],
               [0, 1, 0, dt],
               [0, 0, 1, 0],
               [0, 0, 0, 1]])

# Define the Control Input Matrix B
B = np.matrix([[(dt ** 2) / 2, 0],
               [0, (dt ** 2) / 2],
               [dt, 0],
               [0, dt]])

# Define Measurement Mapping Matrix
H = np.matrix([[1, 0, 0, 0],
               [0, 1, 0, 0]])

# Initial Process Noise Covariance
Q = np.matrix([[(dt ** 4) / 4, 0, (dt ** 3) / 2, 0],
               [0, (dt ** 4) / 4, 0, (dt ** 3) / 2],
               [(dt ** 3) / 2, 0, dt ** 2, 0],
               [0, (dt ** 3) / 2, 0, dt ** 2]]) * std_acc ** 2

# Initial Measurement Noise Covariance
R = np.matrix([[x_std_meas ** 2, 0],
               [0, y_std_meas ** 2]])

# Initial Covariance Matrix
P = np.eye(A.shape[1])

predictedPosx, predictedPosY = [], []
updatePosX, updatePosY = [], []
mesurmentX, mesurmentY = [], []

while True:
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

    x = np.dot(A, x) + np.dot(B, u)

    P = np.dot(np.dot(A, P), A.T) + Q

    if len(x[0]) > 1:
        predictedPosx.append(x[0, 0])
        predictedPosY.append(x[0, 1])

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if not (1300 < area < 2500):
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / h
        if not (0.5 < aspect < 5.0):
            continue

        # Accepted object → draw it
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.rectangle(mask_vis, (x, y), (x + w, y + h), (0, 255, 0), 2)

        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            mesurmentX.append(cx)
            mesurmentY.append(cy)
            # cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
            # cv2.circle(mask_vis, (cx, cy), 4, (0, 0, 255), -1)

            S = np.dot(H, np.dot(P, H.T)) + R

            K = np.dot(np.dot(P, H.T), np.linalg.inv(S))  # Eq.(11)

            z = np.matrix([[cx], [cy]])

            x = x + np.dot(K, (z - np.dot(H, x)))

            I = np.eye(A.shape[0])

            # Update error covariance matrix
            P = (I - (K @ H)) @ P
            updatePosX.append(x[0, 0])
            updatePosY.append(x[0, 1])

    cv2.imshow("Frame", frame)
    cv2.imshow("Mask", mask_vis)

    if cv2.waitKey(30) & 0xFF == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()

plt.plot(predictedPosx, predictedPosY)
plt.plot(updatePosX, updatePosY)
plt.plot(mesurmentX, mesurmentY)
plt.show()
