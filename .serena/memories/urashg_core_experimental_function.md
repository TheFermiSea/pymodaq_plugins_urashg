# Core uRASHG Experimental Function Analysis

## Function Signature and Parameters
```python
def uRASHG(angle_step, wstart, wstop, wstep, pstart, pstop, pnum, filepathtosave, returndata=False)
```

## Key Experimental Parameters
- **angle_step**: Angular resolution for HWP rotation (degrees)
- **wstart, wstop, wstep**: Wavelength scan range (nm) and step size
- **pstart, pstop, pnum**: Power range (W) and number of power points (logarithmic spacing)
- **filepathtosave**: Data storage directory path

## Experimental Workflow Overview

### 1. Data Structure Initialization
- **3D Image Data**: `[y, x, ExcWavelength, alpha]` - Camera images at each wavelength and HWP angle
- **Voltage Data**: `[ExcWavelength, alpha]` - Photodiode voltage measurements
- **Spectral Data**: `[ExcWavelength, Photon Energy, alpha]` - Spectrometer data

### 2. Multi-Nested Loop Structure
```
FOR each power level:
  FOR each wavelength:
    FOR each HWP angle (alpha):
      - Rotate HWP to alpha/2
      - Rotate analyzer HWP to (360-25-alpha/2)
      - Acquire camera sequence (5 frames)
      - Record photodiode voltage
      - Record spectrometer data
```

### 3. Critical Hardware Control Sequence
- **Laser Control**: MaiTai wavelength tuning, shutter control
- **Power Control**: Variable attenuator with Malus law calibration
- **Polarization Control**: Dual HWP system (800nm and 400nm positions)
- **Detection**: Camera (with ROI), photodiode, spectrometer

### 4. Data Acquisition Protocol
- Background subtraction for each wavelength
- Frame averaging (5 frames per measurement)
- Variance calculation for error analysis
- Live exposure time adjustment based on power level

## Key Hardware Instruments Identified
- **mt**: MaiTai laser (wavelength, shutter)
- **cam**: Camera with sequence acquisition
- **spec**: Spectrometer 
- **pd**: Photodiode
- **h800, h400**: HWP rotators for 800nm and 400nm
- **varatten**: Variable attenuator
- **signal**: Signal generator for triggering

## Data Storage Strategy
- Separate HDF5 files for each power level
- Three data types per power: images, voltages, spectra
- Return measurements at end of each power cycle
- Metadata includes power, exposure, date, instrument settings