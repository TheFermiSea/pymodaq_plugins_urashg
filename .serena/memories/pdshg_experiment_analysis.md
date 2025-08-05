# Power-Dependent SHG (PDSHG) Experiment Analysis

## Function Signature
```python
def PDSHG(angle_step, wstart, wstop, wstep, pstart, pstop, pnum, filepathtosave, returndata=False, alpha_offset=0)
```

## Key Differences from Core uRASHG
- **No Camera Acquisition**: Only photodiode voltage and spectrometer data
- **Power-First Loop Structure**: Optimized for power-dependent measurements
- **Signal Generator Control**: Explicit amplitude and offset control
- **Alpha Offset Parameter**: Allows polarization reference adjustment

## Experimental Workflow

### 1. Data Structure (3D instead of 4D)
- **Voltage Data**: `[ExcWavelength, Power, alpha]` - Photodiode measurements
- **Spectral Data**: `[ExcWavelength, Power, Photon Energy, alpha]` - Spectrometer data

### 2. Optimized Loop Structure
```
FOR each wavelength:
  FOR each power level:
    FOR each HWP angle (alpha):
      - Set variable attenuator for target power
      - Rotate HWPs with optional offset
      - Record photodiode voltage (100 samples)
      - Record spectrometer data (5 acquisitions)
```

### 3. Power Control Strategy
- **Descending Power Order**: Start with highest power to minimize thermal effects
- **Malus Law Calibration**: `invmalus(power, wavelength)` function for attenuator
- **Extended Power Range**: Additional power point for reference

### 4. Signal Processing
- **Background Subtraction**: Multiple spectrum averaging (5-10 acquisitions)
- **Statistical Sampling**: 100 photodiode samples per measurement
- **Continuous Data Saving**: HDF5 updates after each power level

## Key Hardware Control Patterns
- **Wavelength Tuning**: Wait 60s after wavelength change for stabilization
- **Shutter Control**: Synchronized with measurement cycles
- **Home Positioning**: HWPs rehomed at each power level
- **Power Stabilization**: Variable attenuator adjustment per measurement

## Data Analysis Features
- Real-time progress bars for all loop levels
- Metadata preservation (exposure, date, instrument settings)
- Power scaling (W to mW for display)
- Separate file storage for voltage and spectral data