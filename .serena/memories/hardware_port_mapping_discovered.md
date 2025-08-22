# HARDWARE PORT MAPPING - REAL TESTED RESULTS

## Discovered Device Ports

**ESP300 Motion Controller**: `/dev/ttyUSB3` at 19200 baud
- Response: "ESP300 Version 3.04 07/27/01"
- Confirmed working with *IDN? command

**Elliptec Rotation Mounts**: 
- Mount 2: `/dev/ttyUSB0` at 9600 baud (ASCII response)
- Mount 3: `/dev/ttyUSB1` at 9600 baud (binary response)
- Both respond to address-specific commands (2in, 3in)

**Newport 1830-C Power Meter**: `/dev/ttyS0` (previously confirmed working)

**Photometrics PrimeBSI Camera**: PyVCAM interface (previously confirmed working)

**MaiTai Laser**: Status unclear
- Previous scanner detected it on `/dev/ttyUSB2`
- Direct serial testing inconclusive
- May be on different port or have specific communication protocol

## Port Allocation Summary

- `/dev/ttyUSB0`: Elliptec Mount 2 (FTDI FT230X)
- `/dev/ttyUSB1`: Elliptec Mount 3 (FTDI FT231X) 
- `/dev/ttyUSB2`: Unknown (Silicon Labs CP2102) - possibly MaiTai
- `/dev/ttyUSB3`: ESP300 Motion Controller (FTDI USB-Serial Cable)
- `/dev/ttyUSB4-6`: Available (FTDI USB-Serial Cable hub)
- `/dev/ttyS0`: Newport 1830-C Power Meter

## Critical Discovery

The user was absolutely correct - I was using wrong ports and making assumptions instead of actually testing hardware communication. This systematic approach identified the real port assignments.