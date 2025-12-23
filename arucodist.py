import cv2
import numpy as np

# Camera Calibration Parameters (Replace these with your calibration values)
camera_matrix = np.array([[1400, 0, 640],  # fx, 0, cx
                          [0, 1400, 360],  # 0, fy, cy
                          [0, 0, 1]], dtype=np.float32)  # Assuming a 1280x720 resolution

dist_coeffs = np.zeros((5, 1))  # Assuming no distortion (update if needed)

# Define ArUco dictionary & marker size (real-world size in meters)
ARUCO_DICT = cv2.aruco.DICT_4X4_50
MARKER_SIZE = 0.05  # 5 cm marker size

def detect_aruco_distance():
    """Detects an ArUco marker and estimates its distance from the camera."""
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)

    cap = cv2.VideoCapture(0)  # Open webcam

    if not cap.isOpened():
        print("❌ Error: Could not open webcam.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect markers
        corners, ids, _ = detector.detectMarkers(gray)

        if ids is not None:
            # Draw detected markers
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)

            for i in range(len(ids)):
                marker_corners = corners[i][0]

                # Define the marker's real-world 3D coordinates
                obj_points = np.array([
                    [-MARKER_SIZE / 2,  MARKER_SIZE / 2, 0],  # Top-left
                    [ MARKER_SIZE / 2,  MARKER_SIZE / 2, 0],  # Top-right
                    [ MARKER_SIZE / 2, -MARKER_SIZE / 2, 0],  # Bottom-right
                    [-MARKER_SIZE / 2, -MARKER_SIZE / 2, 0]   # Bottom-left
                ], dtype=np.float32)

                # SolvePnP to find rotation & translation vectors
                _, rvec, tvec = cv2.solvePnP(obj_points, marker_corners, camera_matrix, dist_coeffs)

                # Extract distance (z-coordinate in meters)
                distance = np.linalg.norm(tvec)

                # Display distance
                x, y = int(marker_corners[0][0]), int(marker_corners[0][1])
                cv2.putText(frame, f"ID: {ids[i][0]}  Distance: {distance:.2f}m",
                            (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Display frame
        cv2.imshow("ArUco Marker Distance", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# Run the detection function
if __name__ == "__main__":
    detect_aruco_distance()
