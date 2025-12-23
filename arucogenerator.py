import cv2
import numpy as np

# ========================== ArUco Marker Generation ==========================

def generate_aruco_marker(marker_id=10, marker_size=200, dictionary=cv2.aruco.DICT_4X4_50, filename=None):
    """Generates and saves an ArUco marker image."""
    aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary)
    
    # Generate marker image
    marker_image = cv2.aruco.generateImageMarker(aruco_dict, marker_id, marker_size)
    
    # Default filename if not provided
    if filename is None:
        filename = f"marker_{marker_id}.png"
    
    cv2.imwrite(filename, marker_image)
    print(f"✅ ArUco marker {marker_id} saved as {filename}")

    # Show generated marker
    cv2.imshow(f"Marker {marker_id}", marker_image)
    cv2.waitKey(5000)  # Show for 500ms (adjust as needed)
    cv2.destroyAllWindows()

# ========================== Generate Multiple Markers ==========================

if __name__ == "__main__":
    # Generate markers with different IDs
    for marker_id in range(5):  # Change range as needed (e.g., 0-49 for DICT_4X4_50)
        generate_aruco_marker(marker_id=marker_id)
