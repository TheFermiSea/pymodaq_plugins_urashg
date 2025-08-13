# PyMoDAQ Extension Architecture Analysis

## URASHG_App Class Structure
The PyMoDAQ extension provides a complete GUI-based experimental control interface for μRASHG experiments.

## Key Components

### 1. Settings Tree Structure
**Hierarchical Parameter Organization**:
- **Experiment Settings**: Save path, filename, date, EOM calibration file
- **Scan Parameters**: Multi-dimensional scan ranges (wavelength, theta, phi, power)
- **Stage Settings**: Hardware offsets for all rotators (Q800, H800, H400)
- **Camera Settings**: ROI definition and exposure settings
- **Status**: Real-time experimental status indicators

### 2. Hardware Integration Pattern
**Dashboard Module Access**:
```python
self.maitai = self.dashboard.get_module('MaiTai')
self.power_meter = self.dashboard.get_module('Newport1830C')
self.h800 = self.dashboard.get_module('H800')
self.h400 = self.dashboard.get_module('H400') 
self.q800 = self.dashboard.get_module('Q800')
self.camera = self.dashboard.get_module('PVCAM')
```

### 3. Data Structure Design
**Multi-Dimensional Arrays**:
- **Voltage Data**: `[theta, phi, ExcWavelength, Power]`
- **Camera Data**: `[y, x, ExcWavelength, theta, phi, Power]`
- **ScipyData Arrays**: Comprehensive coordinate system with units

### 4. GUI Layout Architecture
**Dock-based Interface**:
- **Settings Dock**: Parameter tree widget for experimental control
- **Camera Dock**: Real-time 2D image display
- **Voltage Dock**: Real-time 0D voltage monitoring
- **Menu System**: File operations and experiment control

### 5. Experimental Control Loop
**Nested Loop Structure**:
```
FOR wavelength:
  FOR power:
    FOR phi (QWP angle):
      FOR theta (HWP angle):
        - Move all rotators to target positions
        - Control laser power via EOM
        - Acquire camera frame and voltage
        - Update displays
        - Save data periodically
```

## Key Control Patterns

### 1. Hardware Initialization Sequence
```python
1. Close shutter (laser off)
2. Set camera exposure time
3. Home all rotators to reference positions
4. Initialize EOM calibration system
```

### 2. Power Control Integration
- **EOM Calibration Lookup**: wavelength + power → EOM voltage
- **PID Feedback Control**: Real-time voltage adjustment
- **Tolerance-based Convergence**: ±0.1% power accuracy

### 3. Real-time Data Display
- **Live Camera Viewer**: Background-subtracted frames
- **Voltage Monitoring**: Real-time photodiode signals
- **Parameter Status**: Current experimental coordinates

### 4. Data Management
- **Periodic Saving**: Automatic HDF5 data saves during experiment
- **Coordinate Preservation**: Complete metadata and units
- **Background Subtraction**: Automatic baseline correction

## PyMoDAQ Integration Benefits
1. **Modular Hardware Access**: Standardized instrument interfaces
2. **GUI Framework**: Professional experimental control interface
3. **Data Structures**: Scientific data arrays with metadata
4. **Real-time Visualization**: Live experiment monitoring
5. **Parameter Management**: Hierarchical settings with validation

## Scalability Features
- **Experiment Pause/Resume**: Mid-experiment control
- **Parameter Adjustment**: Real-time experimental modification
- **Multi-instrument Coordination**: Synchronized hardware control
- **Error Handling**: Graceful failure recovery