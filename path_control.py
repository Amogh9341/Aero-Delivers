import asyncio
import math
from mavsdk import System

async def fly_to_coordinates(lat, lon, relative_altitude_m):
    """
    Fly to specified coordinates, wait 10 seconds, then return to launch site.
    
    Args:
        lat (float): Destination latitude in degrees
        lon (float): Destination longitude in degrees
        relative_altitude_m (float): Relative altitude in meters (height above takeoff point)
    """
    # Initialize drone
    drone = System()
    
    # Connect to the drone
    await drone.connect(system_address="udp://:14540")
    
    # Wait for drone to connect
    print("Waiting to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("Connected!")
            break
    
    # Check if drone is ready
    print("Waiting for drone to have a global position estimate...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok:
            print("Global position estimate ok")
            break
    
    # Get (0,0) of drone frame then making it move assuming inputs are w.r.t (0,0)
    gps_origin = await drone.telemetry.get_gps_global_origin()
    lati = gps_origin.latitude_deg
    loni = gps_origin.longitude_deg
    lat += lati
    lon += loni
    
    # Get ground level altitude (to convert relative to absolute)
    ground_altitude = await get_ground_altitude(drone)
    absolute_altitude_m = ground_altitude + relative_altitude_m

    
    
    # Get current position for yaw calculation
    current_position = await get_current_position(drone)
    print(f"Current position: {current_position}")
    
    # Calculate yaw angle to face the destination
    yaw_angle = calculate_yaw(current_position, (lat, lon))
    print(f"Calculated yaw angle: {yaw_angle} degrees")
    
    # Arm the drone
    print("Arming")
    await drone.action.arm()
    
    # Take off
    print("Taking off")
    await drone.action.takeoff()
    
    # Wait for drone to reach takeoff altitude
    print("Waiting for takeoff to complete...")
    await asyncio.sleep(5)
    
    # Go to destination
    print(f"Going to destination: lat={lat}, lon={lon}, relative altitude={relative_altitude_m}m")
    await drone.action.goto_location(lat, lon, absolute_altitude_m, yaw_angle)
    
    # Monitor position until reaching destination
    print("Monitoring position until destination is reached...")
    await wait_for_position(drone, lat, lon, tolerance=0.0001)  # ~10 meters tolerance
    
    # Wait at destination for 10 seconds
    print("Destination reached")
    await drone.action.land()
    await asyncio.sleep(10)


    # Get current position for yaw calculation
    current_position = await get_current_position(drone)
    print(f"Current position: {current_position}")

    # Co-ordinates change
    lat = lati
    lon = loni
    
    # Calculate yaw angle to face the destination
    yaw_angle = calculate_yaw(current_position, (lat, lon))
    print(f"Calculated yaw angle: {yaw_angle} degrees")

    # Arm the drone
    print("Arming")
    await drone.action.arm()

    # Take off
    print("Taking off")
    await drone.action.set_takeoff_altitude(relative_altitude)
    await drone.action.takeoff()

    # Wait for drone to reach takeoff altitude
    print("Waiting for takeoff to complete...")
    await asyncio.sleep(5)
    
    # Return to launch site
    print("Returning to launch site")
    await drone.action.goto_location(lat, lon, absolute_altitude_m, yaw_angle)
    
    # Monitor position until reaching destination
    print("Monitoring position until launch destination is reached...")
    await wait_for_position(drone, lat, lon, tolerance=0.0001)  # ~10 meters tolerance
    
    # Wait for drone to complete return journey
    print("Waiting for drone to return to launch site...")
    await drone.action.land()
    await asyncio.sleep(10)  # Arbitrary wait time, might need adjustment
    print("Mission complete!")

async def get_current_position(drone):
    """Get the current position of the drone."""
    async for position in drone.telemetry.position():
        return (position.latitude_deg, position.longitude_deg)

async def get_ground_altitude(drone):
    """Get the ground altitude (MSL) at the current location."""
    async for position in drone.telemetry.position():
        return position.absolute_altitude_m

async def wait_for_position(drone, target_lat, target_lon, tolerance=0.0001):
    """Wait until the drone reaches the target position within tolerance."""
    while True:
        current_pos = await get_current_position(drone)
        if (abs(current_pos[0] - target_lat) < tolerance and 
            abs(current_pos[1] - target_lon) < tolerance):
            return
        await asyncio.sleep(1)

def calculate_yaw(current_pos, destination_pos):
    """Calculate the yaw angle to face the destination from current position."""
    current_lat, current_lon = current_pos
    dest_lat, dest_lon = destination_pos
    
    # Simple calculation for yaw direction
    yaw_angle = math.degrees(math.atan2(
        (dest_lon - current_lon), 
        (dest_lat - current_lat)
    ))
    
    # Ensure yaw is between 0 and 360 degrees
    if yaw_angle < 0:
        yaw_angle += 360
    
    return yaw_angle

# Example usage
if __name__ == "__main__":
    # Example coordinates (replace with actual coordinates)
    destination_lat = 0.0002
    destination_lon = 0.0002
    relative_altitude = 1.5  # meters relative to takeoff point
    
    # Run the function
    asyncio.run(fly_to_coordinates(destination_lat, destination_lon, relative_altitude))
