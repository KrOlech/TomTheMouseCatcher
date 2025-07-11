import numpy as np
import matplotlib.pyplot as plt

# Simulated ground truth and noisy measurements
#np.random.seed(42)
n_steps = 50
true_velocity = 1.0
true_position = np.linspace(0, true_velocity * n_steps, n_steps)
measurement_noise_std = 2.0
measurements = true_position + np.random.normal(0, measurement_noise_std, n_steps)

# Kalman Filter setup
dt = 1.0  # time step
x = np.array([[0], [0]])  # initial state: [position, velocity]
P = np.eye(2) * 500  # initial uncertainty
F = np.array([[1, dt],
              [0, 1]])  # state transition model
H = np.array([[1, 0]])  # measurement model (we measure position only)
R = np.array([[measurement_noise_std**2]])  # measurement noise
Q = np.array([[0.1, 0],
              [0, 0.1]])  # process noise

# Store results
estimated_positions = []

for z in measurements:
    # Prediction
    x = F @ x
    P = F @ P @ F.T + Q

    # Update
    y = np.array([[z]]) - H @ x                    # innovation
    S = H @ P @ H.T + R                            # innovation covariance
    K = P @ H.T @ np.linalg.inv(S)                 # Kalman Gain

    x = x + K @ y                                  # update estimate
    P = (np.eye(2) - K @ H) @ P                    # update uncertainty

    estimated_positions.append(x[0, 0])            # save position estimate

# Plotting
plt.figure(figsize=(10, 6))
plt.plot(true_position, label="True Position", color='g')
plt.plot(measurements, label="Noisy Measurements", linestyle='dotted', color='r')
plt.plot(estimated_positions, label="Kalman Estimate", color='b')
plt.legend()
plt.xlabel("Time Step")
plt.ylabel("Position")
plt.title("1D Kalman Filter Example")
plt.grid(True)
plt.show()
