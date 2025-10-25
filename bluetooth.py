import asyncio
import sys
import platform
from bleak import BleakScanner, BleakClient
from bleak.backends.device import (
    BLEDevice, # Correct class name for the device object
)  # Type hint for discovered devices

# ----------------------------------------------------------------------
# 1. Device Discovery and Selection
# ----------------------------------------------------------------------

async def scan_and_select_device() -> BLEDevice | None:
    """Scans for Bluetooth Low Energy devices and lets the user select one."""
    print("--- Scanning for nearby Bluetooth LE devices (up to 10 seconds) ---")
    
    # Perform the scan. This returns a list of BLEDevice objects.
    devices = await BleakScanner.discover(timeout=10.0)
    
    # Filter out devices without names for cleaner display
    devices = [dev for dev in devices if dev.name is not None]
    
    if not devices:
        print("\nNo Bluetooth LE devices found.")
        return None

    print(f"\nFound {len(devices)} devices:")
    
    # Print list for user selection
    for i, device in enumerate(devices):
        # Safely retrieve RSSI, defaulting to None if the attribute is missing
        current_rssi = getattr(device, 'rssi', None)
        # Display the index, name, and address of the device
        rssi_info = f" (RSSI: {current_rssi} dBm)" if current_rssi is not None else ""
        print(f"[{i:02d}] {device.name} @ {device.address}{rssi_info}")

    while True:
        try:
            choice = input("\nEnter the number of the device to inspect, or 'q' to quit: ")
            if choice.lower() == 'q':
                return None
            
            index = int(choice)
            if 0 <= index < len(devices):
                print(f"\nSelected: {devices[index].name}")
                return devices[index]
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number or 'q'.")

# ----------------------------------------------------------------------
# 2. Device Introspection (Connection and Data Retrieval)
# ----------------------------------------------------------------------

async def get_device_data(device: BLEDevice):
    """Connects to a selected device and prints all available data (GATT structure)."""
    
    # Safely retrieve RSSI for display in the detailed view
    current_rssi = getattr(device, 'rssi', None)

    # Print basic info
    print("\n--- Device Information ---")
    print(f"Name: {device.name}")
    print(f"Address: {device.address}")
    # Print RSSI, or indicate if it was unavailable/missing
    print(f"Signal Strength (RSSI): {current_rssi} dBm" if current_rssi is not None else "Signal Strength (RSSI): Not Available during scan")
    print(f"Platform: {platform.system()}")
    
    # Attempt to connect and introspect
    try:
        # Use an asynchronous context manager for clean connection/disconnection
        async with BleakClient(device.address) as client:
            if client.is_connected:
                print("\n--- Connection Successful! Retrieving GATT Services ---")
                
                # Retrieve and print services, characteristics, and descriptors
                services = client.services
                print(f"\nTotal Services Found: {len(services)}")
                
                for service in services:
                    # Print Service details (UUID and description)
                    print(f"\n  [SERVICE] UUID: {service.uuid} (Handle: {service.handle}, Description: {service.description})")
                    
                    for char in service.characteristics:
                        # Print Characteristic details (UUID, properties, description)
                        properties = ", ".join(char.properties)
                        print(f"    [CHAR] UUID: {char.uuid} (Properties: {properties}, Handle: {char.handle})")
                        
                        # Attempt to read the characteristic's value if allowed
                        if "read" in char.properties:
                            try:
                                value = await client.read_gatt_char(char.uuid)
                                # Decode bytes to a string (or display hex if undecodable)
                                try:
                                    decoded_value = value.decode('utf-8', errors='ignore').strip()
                                except UnicodeDecodeError:
                                    decoded_value = f"Hex: {value.hex()}"
                                
                                # Limit display length for readability
                                if len(decoded_value) > 80:
                                    decoded_value = decoded_value[:80] + "..."
                                    
                                print(f"      [VALUE] {decoded_value}")
                                
                            except Exception as e:
                                print(f"      [ERROR] Could not read value: {e}")

                        for descriptor in char.descriptors:
                            # Print Descriptor details
                            print(f"      [DESC] UUID: {descriptor.uuid} (Handle: {descriptor.handle})")
                            
            else:
                print("\n--- Connection Failed ---")
                
    except Exception as e:
        print(f"\nAn error occurred during connection or data retrieval: {e}")
        print("Note: Many BLE devices (like phones or some headphones) actively refuse connections from external scanners.")

# ----------------------------------------------------------------------
# 3. Main Execution
# ----------------------------------------------------------------------

async def main():
    """Main function to run the Bluetooth inspection workflow."""
    selected_device = await scan_and_select_device()
    
    if selected_device:
        await get_device_data(selected_device)
        print("\n--- Inspection Complete ---")
    else:
        print("\n--- Program Exited ---")

if __name__ == "__main__":
    if platform.system() == "Windows" and sys.version_info < (3, 7):
        # Windows requires ProactorEventLoop for Bleak
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    try:
        # Run the asynchronous main function
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user.")
    except Exception as e:
        # This catches errors not specifically handled above
        print(f"\nAn unexpected error occurred during execution: {e}")
