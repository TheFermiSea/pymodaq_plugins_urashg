# Hardware Control Sequences and Integration Patterns

## Hardware Component Architecture

### 1. Core Instrument Set
- **MaiTai Laser**: Wavelength tuning, shutter control, power monitoring
- **EOM System**: Voltage-controlled power modulation with PID feedback
- **Elliptec Rotators**: HWP and QWP positioning (H800, H400, Q800)
- **Camera (PVCAM)**: 2D imaging with ROI support and sequence acquisition
- **Spectrometer**: Spectral analysis with configurable parameters
- **Newport Power Meter**: Independent power verification
- **Photodiode**: Real-time power monitoring for EOM feedback
- **Signal Generator**: Triggering and synchronization control

### 2. Control Sequence Patterns

#### Experiment Initialization
```python
1. Close laser shutter (safety)
2. Home all rotators to reference positions
3. Set camera exposure time and ROI
4. Configure signal generator parameters
5. Load EOM calibration data
6. Set initial laser wavelength
7. Configure spectrometer settings
```

#### Wavelength Change Protocol
```python
1. Set laser shutter off
2. Change MaiTai wavelength
3. Wait 60 seconds for stabilization
4. Take background spectrum
5. Adjust EOM calibration for new wavelength
6. Verify power stability
```

#### Power Control Sequence (EOM)
```python
1. Lookup EOM voltage from calibration: wavelength + power → voltage
2. Set initial EOM voltage
3. Start PID feedback loop:
   - Read photodiode voltage (10 samples averaged)
   - Compare to target voltage
   - Adjust EOM voltage via PID controller
   - Repeat until convergence (±0.1% tolerance)
4. Verify power with independent power meter
```

#### Polarization State Setting
```python
1. Calculate target angles for each rotator
2. Move rotators sequentially:
   - Q800: QWP for ellipticity control
   - H800: HWP for incident polarization (angle/2)
   - H400: HWP for analyzer (360-25-angle/2)
3. Allow settling time (0.1s per rotator)
4. Verify final positions
```

### 3. Data Acquisition Protocols

#### Camera Sequence Acquisition
```python
1. Start camera live mode
2. Acquire sequence (typically 5 frames)
3. Calculate frame statistics:
   - Mean frame for signal
   - Variance frame for error analysis
4. Background subtraction
5. Store with coordinate metadata
```

#### Synchronized Multi-Instrument Measurement
```python
1. Set all hardware to measurement state
2. Open laser shutter
3. Simultaneously record:
   - Camera frame sequence
   - Photodiode voltage (100 sample average)
   - Spectrometer spectrum
4. Close laser shutter
5. Process and store all data with timestamps
```

### 4. Error Handling and Safety

#### Hardware Safety Protocols
```python
1. Shutter closed by default (laser off)
2. Rotator position verification before movement
3. Power level validation before EOM adjustment
4. Emergency stop capability at all loop levels
5. Automatic timeout for stuck operations
```

#### Data Quality Assurance
```python
1. Power stability verification:
   - Check variance/mean ratio < 1e-5
   - Retry if power unstable
2. Background verification:
   - Ensure proper shutter operation
   - Validate background subtraction
3. Instrument response checking:
   - Verify rotator position feedback
   - Check camera frame validity
```

### 5. Timing and Synchronization

#### Critical Timing Parameters
- **Wavelength stabilization**: 60 seconds after change
- **Rotator settling**: 0.1 seconds per movement
- **PID control loop**: 0.0001 second update interval
- **Camera frame acquisition**: Variable based on exposure
- **Power stabilization**: Variable based on PID convergence

#### Synchronization Strategies
```python
1. Signal generator triggers for camera/spectrometer sync
2. Sequential instrument control to avoid conflicts
3. Progress bars for multi-level loop monitoring
4. Real-time status updates during long experiments
```

### 6. Calibration Integration

#### Runtime Calibration Usage
```python
1. EOM Power Control:
   - Load calibration file at startup
   - Interpolate voltage for current wavelength/power
   - Apply correction factors (1.065x voltage, 0.98x target)

2. Rotator Positioning:
   - Apply hardware-specific offsets
   - Account for optical axis alignment
   - Use Malus law fitting for power control

3. Spectral Calibration:
   - Wavelength-to-energy conversion
   - Grating efficiency correction
   - Slit width optimization
```

### 7. PyMoDAQ Integration Patterns

#### Module Access Pattern
```python
# Access hardware through dashboard
self.maitai = self.dashboard.get_module('MaiTai')
self.camera = self.dashboard.get_module('PVCAM')
self.h800 = self.dashboard.get_module('H800')
```

#### Parameter Synchronization
```python
# GUI parameter tree updates hardware settings
wavelength_param.sigValueChanged.connect(self.update_wavelength)
power_param.sigValueChanged.connect(self.update_power)
```

#### Real-time Display Integration
```python
# Live data display during experiments
self.viewer2D.show(camera_frame)
self.viewer0D.show(voltage_data)
QtWidgets.QApplication.processEvents()  # GUI responsiveness
```

## Key Control Insights for Implementation

### 1. Sequential vs Parallel Control
- **Sequential**: Wavelength changes, power adjustments (avoid conflicts)
- **Parallel**: Multi-instrument data acquisition (when synchronized)

### 2. Feedback Control Requirements
- **EOM**: Closed-loop PID for stable power control
- **Rotators**: Open-loop positioning with verification
- **Camera**: Exposure time adjustment based on power level

### 3. Calibration Dependencies
- **All experiments require pre-calibration data**
- **Runtime interpolation for intermediate values**
- **Wavelength-dependent corrections essential**

### 4. Error Recovery Strategies
- **Graceful degradation on hardware failures**
- **Automatic retry with parameter adjustment**
- **Manual intervention points for complex issues**