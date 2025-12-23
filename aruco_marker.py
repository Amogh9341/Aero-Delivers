import asyncio
import numpy as np
import cv2
import RPi.GPIO as GPIO  # Raspberry Pi GPIO library
from mavsdk import System
from mavsdk.mission import MissionItem, MissionPlan
from mavsdk.offboard import PositionNedYaw, OffboardError

ARUCO_DICT = {
    "DICT_5X5_100": cv2.aruco.DICT_5X5_100
}

SERVO_PIN = 18  # Define the GPIO pin for the servo
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo = GPIO.PWM(SERVO_PIN, 50)
servo.start(0)

def set_servo_angle(angle):
    duty_cycle = (angle / 18) + 2  # Convert angle to duty cycle
    GPIO.output(SERVO_PIN, True)
    servo.ChangeDutyCycle(duty_cycle)
    asyncio.sleep(0.5)
    GPIO.output(SERVO_PIN, False)
    servo.ChangeDutyCycle(0)

def pose_estimation(frame, aruco_dict_type, matrix_coefficients, distortion_coefficients):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    aruco_dict = cv2.aruco.getPredefinedDictionary(aruco_dict_type)
    parameters = cv2.aruco.DetectorParameters()

    corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

    if ids is not None:
        for i in range(len(ids)):
            rvec, tvec, _ = cv2.aruco.estimatePoseSingleMarkers(
                corners[i], 0.02, matrix_coefficients, distortion_coefficients
            )
            cv2.aruco.drawDetectedMarkers(frame, corners)
            cv2.drawFrameAxes(frame, matrix_coefficients, distortion_coefficients, rvec, tvec, 0.01)
            distance = np.linalg.norm(tvec[0][0])
            return tvec[0][0]
    return None

async def run():
    drone = System()
    await drone.connect(system_address="udp://:14540")
    
    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("-- Connected to drone!")
            break
    
    print("Waiting for global position estimate...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("-- Global position estimate OK")
            break
    
    home_position = None
    async for position in drone.telemetry.position():
        home_position = position
        break
    
    mission_items = [
        MissionItem(47.39803986, 8.54557254, 10, 5, True, float('nan'),
                    float('nan'), MissionItem.CameraAction.NONE, float('nan'), float('nan'), float('nan'),
                    0.0, float('nan'), MissionItem.VehicleAction.NONE)
    ]
    mission_plan = MissionPlan(mission_items)
    await drone.mission.upload_mission(mission_plan)

    print("-- Arming")
    await drone.action.arm()
    print("-- Starting mission")
    await drone.mission.start_mission()

    async for mission_progress in drone.mission.mission_progress():
        if mission_progress.current == len(mission_items):
            print("-- Mission complete")
            break
    
    async for position in drone.telemetry.position_velocity_ned():
        new_origin = position.position
        print(f"-- New Origin Set: North={new_origin.north_m}, East={new_origin.east_m}, Down={new_origin.down_m}")
        break
    
    await drone.offboard.set_position_ned(PositionNedYaw(new_origin.north_m, new_origin.east_m, new_origin.down_m, 0.0))
    await drone.offboard.start()
    print("-- Offboard mode started")
    
    cap = cv2.VideoCapture(0)
    intrinsic_camera = np.array(((933.15867, 0, 657.59), (0, 933.1586, 400.36993), (0, 0, 1)))
    distortion = np.array((-0.43948, 0.18514, 0, 0))
    aruco_type = "DICT_5X5_100"

    while cap.isOpened():
        ret, img = cap.read()
        if not ret:
            break

        tvec = pose_estimation(img, ARUCO_DICT[aruco_type], intrinsic_camera, distortion)
        cv2.imshow('Estimated Pose', img)

        if tvec is not None:
            x_offset, y_offset, z_offset = tvec[0] * 10, tvec[1] * 10, tvec[2] * 10
            print(f"Adjusting Position: North={-y_offset:.2f}, East={-x_offset:.2f}, Down={z_offset:.2f}")

            while abs(z_offset - 0.5) > 0.05:
                await drone.offboard.set_position_ned(PositionNedYaw(
                    north_m=new_origin.north_m - y_offset,
                    east_m=new_origin.east_m - x_offset,
                    down_m=new_origin.down_m + z_offset - 0.1,
                    yaw_deg=0.0
                ))
                await asyncio.sleep(1)
                async for telemetry in drone.telemetry.position():
                    z_offset = telemetry.relative_altitude_m
                    break
            
            print("-- 50cm above ArUco, opening servo")
            set_servo_angle(90)
            await asyncio.sleep(2)
            print("-- Closing servo")
            set_servo_angle(0)
            
            print("-- Returning to home")
            await drone.action.return_to_launch()
            break

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    print("-- Stopping offboard mode")
    try:
        await drone.offboard.stop()
    except OffboardError as error:
        print(f"Stopping offboard mode failed with error: {error._result.result}")
    
    cap.release()
    cv2.destroyAllWindows()
    GPIO.cleanup()

if __name__ == "__main__":
    asyncio.run(run())