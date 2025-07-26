#!/usr/bin/env python3
"""
URASHG Hardware Controller - Text Interface
==========================================
Simple command-line interface to control URASHG hardware directly.
"""

import sys
import time
sys.path.insert(0, 'src')

from pymodaq_plugins_urashg.hardware.urashg.maitai_control import MaiTaiController
from pymodaq_plugins_urashg.hardware.urashg.elliptec_wrapper import ElliptecController

class URASHGController:
    def __init__(self):
        self.maitai = None
        self.elliptec = None
        
    def connect_maitai(self):
        """Connect to MaiTai laser."""
        try:
            self.maitai = MaiTaiController(port='/dev/ttyUSB0', mock_mode=False)
            if self.maitai.connect():
                print("✅ MaiTai laser connected")
                return True
            else:
                print("❌ MaiTai connection failed")
                return False
        except Exception as e:
            print(f"❌ MaiTai error: {e}")
            return False
    
    def connect_elliptec(self):
        """Connect to Elliptec mounts."""
        try:
            self.elliptec = ElliptecController(port='/dev/ttyUSB1', mock_mode=False)
            if self.elliptec.connect():
                print("✅ Elliptec mounts connected")
                return True
            else:
                print("❌ Elliptec connection failed")
                return False
        except Exception as e:
            print(f"❌ Elliptec error: {e}")
            return False
    
    def get_maitai_status(self):
        """Get MaiTai status."""
        if not self.maitai or not self.maitai.connected:
            print("❌ MaiTai not connected")
            return
            
        try:
            wavelength = self.maitai.get_wavelength()
            power = self.maitai.get_power()
            shutter = self.maitai.get_shutter_state()
            
            print(f"📊 MaiTai Status:")
            print(f"   Wavelength: {wavelength} nm")
            print(f"   Power: {power} W")
            print(f"   Shutter: {'Open' if shutter else 'Closed'}")
        except Exception as e:
            print(f"❌ Error reading MaiTai: {e}")
    
    def set_wavelength(self, wavelength):
        """Set MaiTai wavelength."""
        if not self.maitai or not self.maitai.connected:
            print("❌ MaiTai not connected")
            return
            
        try:
            print(f"🔄 Setting wavelength to {wavelength} nm...")
            success = self.maitai.set_wavelength(int(wavelength))
            if success:
                print("✅ Wavelength command sent")
                time.sleep(1)  # Wait for tuning
                new_wl = self.maitai.get_wavelength()
                print(f"✅ New wavelength: {new_wl} nm")
            else:
                print("❌ Wavelength setting failed")
        except Exception as e:
            print(f"❌ Error setting wavelength: {e}")
    
    def get_elliptec_positions(self):
        """Get Elliptec positions."""
        if not self.elliptec or not self.elliptec.connected:
            print("❌ Elliptec not connected")
            return
            
        try:
            positions = self.elliptec.get_all_positions()
            print(f"📊 Elliptec Positions:")
            for addr, pos in positions.items():
                mount_name = {'2': 'HWP incident', '3': 'QWP', '8': 'HWP analyzer'}.get(addr, f'Mount {addr}')
                print(f"   {mount_name}: {pos:.2f}°")
        except Exception as e:
            print(f"❌ Error reading Elliptec: {e}")
    
    def move_mount(self, address, position):
        """Move specific mount."""
        if not self.elliptec or not self.elliptec.connected:
            print("❌ Elliptec not connected")
            return
            
        try:
            print(f"🔄 Moving mount {address} to {position}°...")
            success = self.elliptec.move_absolute(address, float(position))
            if success:
                print("✅ Move command sent")
                time.sleep(2)  # Wait for movement
                new_pos = self.elliptec.get_position(address)
                print(f"✅ New position: {new_pos:.2f}°")
            else:
                print("❌ Move command failed")
        except Exception as e:
            print(f"❌ Error moving mount: {e}")
    
    def disconnect_all(self):
        """Disconnect all devices."""
        if self.maitai:
            self.maitai.disconnect()
            print("✅ MaiTai disconnected")
        if self.elliptec:
            self.elliptec.disconnect()
            print("✅ Elliptec disconnected")

def main():
    controller = URASHGController()
    
    print("🔬 URASHG Hardware Controller")
    print("=" * 40)
    print("Commands:")
    print("  connect_maitai    - Connect to MaiTai laser")
    print("  connect_elliptec  - Connect to Elliptec mounts")
    print("  maitai_status     - Get MaiTai status")
    print("  set_wl <nm>       - Set wavelength (e.g., set_wl 800)")
    print("  elliptec_status   - Get mount positions")
    print("  move <addr> <deg> - Move mount (e.g., move 2 45.0)")
    print("  quit              - Exit")
    print()
    
    while True:
        try:
            cmd = input("urashg> ").strip().split()
            if not cmd:
                continue
                
            if cmd[0] == "quit":
                break
            elif cmd[0] == "connect_maitai":
                controller.connect_maitai()
            elif cmd[0] == "connect_elliptec":
                controller.connect_elliptec()
            elif cmd[0] == "maitai_status":
                controller.get_maitai_status()
            elif cmd[0] == "set_wl" and len(cmd) > 1:
                controller.set_wavelength(cmd[1])
            elif cmd[0] == "elliptec_status":
                controller.get_elliptec_positions()
            elif cmd[0] == "move" and len(cmd) > 2:
                controller.move_mount(cmd[1], cmd[2])
            else:
                print("❌ Unknown command or missing arguments")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n🔄 Disconnecting...")
    controller.disconnect_all()
    print("👋 Goodbye!")

if __name__ == "__main__":
    main()