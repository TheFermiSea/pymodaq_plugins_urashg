# EOM Power Control and Calibration Analysis

## EOM Power Control Function
The `set_power()` function implements precise laser power control using EOM voltage modulation with PID feedback control.

## Key Control Parameters
- **PID Coefficients**: kp=24, ki=3, kd=0.0125
- **Update Interval**: 0.0001 seconds (10 kHz control loop)
- **Tolerance**: 0.001 (0.1% accuracy)
- **Voltage Scaling**: 1.065x multiplier, 0.98x target adjustment

## Control Algorithm
```python
# Two-stage calibration approach:
1. EOM Voltage Lookup: wavelength + target_power → initial_EOM_voltage
2. PID Feedback Loop: measured_PD_voltage → EOM_voltage_adjustment
```

## PID Control Logic
- **Target**: Photodiode voltage corresponding to desired power
- **Feedback**: Real-time photodiode voltage measurement (10 samples averaged)
- **Output**: EOM voltage adjustments
- **Convergence**: 5 consecutive measurements within tolerance

## Calibration Data Dependencies
- **EOM Calibration File**: Maps wavelength/power to EOM voltage and expected PD voltage
- **Wavelength-Dependent**: Separate calibration curves for each wavelength
- **Power-Dependent**: Nonlinear EOM response requires lookup tables

## Hardware Integration
- **daq.eom_voltage**: Direct EOM voltage control
- **daq.get_pd_voltage()**: Photodiode feedback with averaging
- **pm.power()**: Independent power meter verification
- **mt.wavelength**: Current laser wavelength for calibration lookup

## Debug and Monitoring
- Real-time voltage/power monitoring
- PID convergence tracking
- Error percentage calculation
- Timing analysis for control loop performance

## Key Insights for PyMoDAQ Implementation
1. **Calibration-Based Control**: Requires pre-calibrated lookup tables
2. **Closed-Loop Feedback**: Essential for stable power control
3. **Wavelength Dependence**: Power control must account for wavelength
4. **Multi-Instrument Coordination**: EOM, photodiode, and power meter integration