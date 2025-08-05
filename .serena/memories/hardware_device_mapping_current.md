# Current Hardware Device Mapping

## Connected Devices (Verified August 2025)

### Camera System
- **PrimeBSI Camera**: `/dev/pvcamUSB_0` - WORKING
  - Detection: PyVCAM 2.2.3 compatible
  - Status: Fully functional with PyMoDAQ plugin
  - Temperature: Live monitoring at -19.89°C

### Laser System  
- **MaiTai Laser**: `/dev/ttyUSB0` - WORKING
  - Communication: Serial interface confirmed
  - Controls: Wavelength tuning and shutter operations
  - Integration: PyMoDAQ plugin fully functional

### Motion Control (Pending Configuration)
- **ESP300 Controller**: Serial hub ports `/dev/ttyUSB3-6`
  - Connection: 4-port serial hub detected
  - Status: Connected but not yet configured
  - Next: Determine correct port assignment

### Power Measurement (Pending Testing)
- **Newport 1830-C Power Meter**: `/dev/ttyS0`
  - Connection: Direct serial connection
  - Status: Connected but not yet tested
  - Next: Verify communication protocol

### USB Device Overview
```
USB0: MaiTai laser (confirmed working)  
USB1: Unknown device
USB2: Unknown device
USB3-6: ESP300 serial hub (4 ports)
```

### Serial Port Overview
```
ttyS0: Newport power meter (direct connection)
ttyUSB0: MaiTai laser
ttyUSB3-6: ESP300 serial hub ports
```