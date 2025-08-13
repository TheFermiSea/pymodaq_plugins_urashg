# Calibration Methods Analysis

## Overview of Calibration Procedures
The urashg_2 repository contains comprehensive calibration procedures for all optical components in the RASHG system.

## 1. EOM Power Calibration (`power_calib_EOM.py`)
**Purpose**: Creates lookup tables for EOM voltage → power conversion
**Procedure**:
- Sweep EOM voltages across range for multiple wavelengths  
- Record photodiode voltage and power meter readings
- Create interpolation tables for power control

**Data Structure**: `[Wavelength, EOMVoltage]` → `{Power, PDVoltage}`

## 2. Variable Attenuator Calibration (`power_calib.py`)
**Purpose**: Malus law calibration for HWP-based power control
**Procedure**:
- Rotate HWP through full range for each wavelength
- Record power vs. angle relationship
- Fit cos²(θ) function: `P = A·cos²(θ - φ) + C`

**Key Parameters**:
- **A**: Maximum power amplitude
- **φ**: Phase offset (optical axis alignment)
- **C**: Baseline power offset

## 3. Ellipticity Calibration (`elipticity_calibration.py`)
**Purpose**: QWP + HWP polarization state calibration
**Multi-dimensional calibration**:
- **QWP angles**: Quarter-wave plate positions
- **HWP angles**: Half-wave plate positions  
- **Analyzer angles**: Detection polarization
- **Wavelengths**: Chromatic dispersion correction

**Data Structure**: `[Wavelength, QWPAngle, HWPAngle, AnalyzerAngle]` → `Power`

## 4. Polarization Calibration (`polarization_calib.py`)
**Purpose**: Multi-rotator system alignment and cross-calibration

### Key Functions:
- **`pol_rotC_calib()`**: Individual rotator characterization
- **`rot_calib()`**: Cross-rotator alignment verification

### Calibration Workflow:
1. Home all rotators to reference positions
2. Set laser wavelength and allow stabilization
3. Sweep one rotator while others are fixed
4. Record power vs. angle for each rotator
5. Fit cos² functions to extract optical parameters

## 5. Calibration Fitting Class (`calibration_fitting.py`)
**Purpose**: Automated curve fitting and parameter extraction

### Core Functions:
- **`cossq(angle, A, phi, C)`**: Malus law fitting function
- **`invcossq(power, params)`**: Inverse function for angle lookup
- **`Calibration` class**: Complete calibration data processing

### Fitting Algorithm:
```python
P(θ) = A·cos²(θ - φ) + C
```
- **A**: Amplitude (maximum transmission)
- **φ**: Phase offset (optical axis)
- **C**: Baseline offset (leakage/background)

## Key Hardware Control Patterns Identified

### 1. Sequential Calibration Protocol:
```python
1. Home all rotators to reference
2. Set wavelength and wait for stabilization (10-60s)
3. Set laser shutter state
4. Sweep measurement parameters
5. Record data with error analysis
6. Fit calibration curves
7. Save interpolation data
```

### 2. Error Handling and Validation:
- Power stability checking before measurement
- Variance-based data quality assessment
- Automatic retry on failed fits
- Bounds checking for fit parameters

### 3. Data Quality Assurance:
- Background subtraction
- Multiple sample averaging
- Statistical variance calculation
- Calibration curve validation

## Calibration Data Dependencies
All experiments require pre-calibrated data files:
- **EOM calibration**: Power control lookup tables
- **Rotator calibration**: Angle-to-power relationships  
- **Polarization calibration**: Multi-element polarization states
- **Wavelength correction**: Chromatic dispersion compensation