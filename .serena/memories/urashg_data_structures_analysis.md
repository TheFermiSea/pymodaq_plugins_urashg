# μRASHG Data Structures and Analysis Patterns

## Core Data Structure Paradigm
All experiments use **ScipyData Arrays** with comprehensive coordinate systems and metadata preservation.

## Multi-Dimensional Coordinate Systems

### 1. Core uRASHG Experiment
```python
# 4D Camera Data: [y, x, ExcWavelength, alpha]
data = sc.zeros(dims=['y', 'x', 'ExcWavelength', 'alpha'],
                shape=[roi[3], roi[2], len(wavelengths), len(hwp_angles)],
                unit=sc.Unit('counts'), with_variances=True)

# 2D Voltage Data: [ExcWavelength, alpha] 
dataV = sc.zeros(dims=['ExcWavelength', 'alpha'],
                 shape=[len(wavelengths), len(hwp_angles)],
                 unit=sc.Unit('V'), with_variances=True)

# 3D Spectral Data: [ExcWavelength, Photon Energy, alpha]
specdata = sc.zeros(dims=['ExcWavelength', 'Photon Energy', 'alpha'],
                    shape=[len(wavelengths), len(energies), len(hwp_angles)],
                    unit=sc.Unit('counts'), with_variances=False)
```

### 2. Power-Dependent Experiments (PDSHG)
```python
# 3D Voltage: [ExcWavelength, Power, alpha]
dataV = sc.zeros(dims=['ExcWavelength', 'Power', 'alpha'],
                 shape=[len(wavelengths), len(powers), len(hwp_angles)])

# 4D Spectral: [ExcWavelength, Power, Photon Energy, alpha]  
specdata = sc.zeros(dims=['ExcWavelength', 'Power', 'Photon Energy', 'alpha'],
                    shape=[len(wavelengths), len(powers), len(energies), len(hwp_angles)])
```

### 3. PyMoDAQ Extension Data (6D Maximum)
```python
# 6D Camera: [y, x, ExcWavelength, theta, phi, Power]
data = sc.zeros(dims=['y', 'x', 'ExcWavelength', 'theta', 'phi', 'Power'],
                shape=[roi[3], roi[2], len(wavelengths), len(theta), len(phi), len(powers)])

# 4D Voltage: [theta, phi, ExcWavelength, Power]
dataV = sc.zeros(dims=['theta', 'phi', 'ExcWavelength', 'Power'],
                 shape=[len(theta), len(phi), len(wavelengths), len(powers)])
```

## Coordinate Definition Patterns

### 1. Angular Coordinates
```python
# HWP rotation angles (degrees)
hwp_angles = sc.arange(dim='alpha', start=0., stop=360.+step, step=step, 
                       unit=sc.units.deg, dtype='int64')

# Theta/Phi angles for polarization analysis
theta = sc.arange(dim='theta', start=0., stop=360., step=8.,
                  unit=sc.Unit('deg'))
phi = sc.arange(dim='phi', start=0., stop=91., step=90.,
                unit=sc.Unit('deg'))
```

### 2. Wavelength Coordinates
```python
# Wavelength ranges (nanometers)
wavelengths = sc.arange(dim='ExcWavelength', start=wstart, stop=wstop+wstep,
                        step=wstep, unit=sc.Unit('nm'), dtype='int64')
```

### 3. Power Coordinates
```python
# Logarithmic power spacing (Watts)
powers = sc.logspace(dim='Power', start=np.log10(pstart), stop=np.log10(pstop),
                     num=pnum, unit=sc.Unit('W'))
```

### 4. Spatial Coordinates
```python
# Camera pixel coordinates
x = sc.arange(dim='x', start=0, stop=roi[2], step=1, unit=sc.Unit('pixel'))
y = sc.arange(dim='y', start=0, stop=roi[3], step=1, unit=sc.Unit('pixel'))
```

## Metadata and Attributes

### Comprehensive Metadata Storage
```python
data.attrs = {
    'power': sc.scalar(power.value, unit=sc.Unit('W')),
    'exposure': sc.scalar(cam.exp_time, unit=sc.Unit('ms')),
    'date': sc.scalar(int(datetime.now().strftime('%Y%m%d%H%M%S'))),
    'slit_width': sc.scalar(spec.slit_width, unit=sc.Unit('um')),
    'grating': sc.scalar(spec.grating, unit=sc.Unit('lines/mm')),
    'center_wavelength': sc.scalar(spec.wavelength, unit=sc.Unit('nm'))
}
```

## Data Processing Patterns

### 1. Background Subtraction
```python
# Automatic background correction
data['alpha', alpha]['ExcWavelength', w] = measurement_frame - background_frame
specdata['alpha', alpha]['ExcWavelength', w] = spectrum - background_spectrum
```

### 2. Variance Tracking
```python
# Statistical variance calculation
frame_variance = sequence.var(axis=0).T
data_with_variance = sc.array(dims=['y','x'], values=frame_mean, 
                              variances=frame_variance, unit=sc.Unit('counts'))
```

### 3. Data Selection and Slicing
```python
# Coordinate-based data access
subset = data['ExcWavelength', wavelength]['alpha', angle]
power_slice = dataV['Power', power_range]
```

## File I/O and Storage

### 1. HDF5 Storage Pattern
```python
# Individual files per experimental condition
data.to_hdf5(f'{filepath}\\{power.value*1000:.4f}mw.h5')
dataV.to_hdf5(f'{filepath}\\{power.value*1000:.4f}mw_V.h5')
specdata.to_hdf5(f'{filepath}\\{power.value*1000:.4f}mw_spec.h5')

# Combined dataset storage
dg = sc.DataGroup({'V': dataV, 'data': data, 'spec': specdata})
dg.save_hdf5(f'{path}/{filename}')
```

### 2. Data Loading and Calibration
```python
# Calibration data loading
powerfit = sc.io.load_hdf5(r'path\to\powercal.h5')
voltagefit = sc.io.load_hdf5(r'path\to\voltagecal.h5')
```

## Analysis Function Patterns

### 1. Real-time Visualization
```python
# Live plotting during experiments
def liveplot(n=200, slit_width=50, wavelength=435, exposure=.1):
    # Continuous spectral monitoring
    while running:
        spectrum = spec.get_spectrum(eV=False)
        spectrum.plot(ax=ax)
        plt.pause(0.0001)
```

### 2. Curve Fitting Integration
```python
# Automatic parameter extraction
popt, params = curve_fit(cossq, data,
                        p0={'A': amplitude, 'phi': phase, 'C': offset},
                        bounds={'A': bounds_A, 'phi': bounds_phi, 'C': bounds_C})
```

## Key Design Principles
1. **Unit Consistency**: All data includes proper scientific units
2. **Coordinate Completeness**: Full dimensional coordinate systems
3. **Metadata Preservation**: Experimental conditions stored with data
4. **Variance Tracking**: Statistical uncertainty propagation
5. **Modular Storage**: Separate files for different data types
6. **Background Correction**: Automatic baseline subtraction
7. **Real-time Access**: Live data visualization during experiments