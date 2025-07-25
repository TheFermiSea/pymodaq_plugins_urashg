# URASHG Microscope PyMoDAQ Plugin Development Plan

## Project Overview

This document outlines the comprehensive development plan for creating a PyMoDAQ plugin package for $\mu$RASHG (micro Rotational Anisotropy Second Harmonic Generation) microscopy systems. The project will leverage container-use for distributed agent-based development, allowing multiple coding agents to work on different components simultaneously in isolated environments.

## System Architecture

### Hardware Components

**Core μRASHG Microscope Stack:**
- **MaiTai Laser** with Electro-Optic Modulator (EOM) for power control
- **Red Pitaya** for FPGA-based PID laser stabilization (base address: 0x40300000)
- **3x Thorlabs ELL14** motorized rotation mounts:
  - QWP (Quarter-Wave Plate) for incident beam
  - HWP (Half-Wave Plate) for incident polarization
  - HWP (Half-Wave Plate) for analyzer
- **Photometrics Prime BSI** sCMOS camera for SHG detection
- **Fast photodiode** for laser power monitoring
- **Galvo mirrors** for beam scanning (future integration)

### PyMoDAQ Plugin Architecture

**Plugin Structure:**
```
pymodaq_plugins_urashg/
├── src/pymodaq_plugins_urashg/
│   ├── daq_move_plugins/              # Actuator control
│   │   ├── daq_move_redpitaya_fpga.py    # PID laser control
│   │   ├── daq_move_elliptec.py          # Polarization control
│   │   └── daq_move_maitai_laser.py      # Laser control
│   ├── daq_viewer_plugins/            # Detection systems
│   │   └── plugins_2D/
│   │       └── daq_2dviewer_pyvcam.py    # Camera interface
│   └── hardware/                      # Hardware abstraction
│       └── urashg/
│           ├── redpitaya_control.py      # FPGA register access
│           ├── elliptec_wrapper.py       # Multi-mount controller
│           ├── maitai_control.py         # Laser communication
│           └── camera_utils.py           # Camera utilities
├── examples/                          # Usage examples
├── docs/                             # Documentation
└── tests/                            # Test suite
```

## Development Workflow with Container-Use

### Agent Distribution Strategy

We will use container-use to delegate development tasks to specialized agents, each working in isolated environments:

**Environment Structure:**
- Each agent gets a containerized sandbox with its own git branch
- Real-time visibility into agent progress and command history
- Ability to intervene directly when agents get stuck
- Standard git workflow for reviewing and merging work

### Recommended Agent Assignments

#### Agent 1: Hardware Abstraction Layer (HAL) Specialist
**Environment ID:** `urashg-hal-dev`
**Responsibilities:**
- Red Pitaya FPGA register mapping and memory-mapped I/O
- Elliptec communication protocol implementation
- MaiTai laser control interface
- Camera hardware abstraction

**Key Deliverables:**
- `hardware/urashg/redpitaya_control.py`
- `hardware/urashg/elliptec_wrapper.py`
- `hardware/urashg/maitai_control.py`
- `hardware/urashg/camera_utils.py`

**Container-Use Commands:**
```bash
# View agent progress
container-use log urashg-hal-dev

# Review work
container-use checkout urashg-hal-dev
```

#### Agent 2: PyMoDAQ Move Plugin Developer
**Environment ID:** `urashg-move-plugins`
**Responsibilities:**
- DAQ_Move_RedPitayaFPGA plugin (dual-purpose move/viewer)
- DAQ_Move_Elliptec multi-axis polarization control
- DAQ_Move_MaiTai laser power and status control
- Settings tree configuration and parameter validation

**Key Deliverables:**
- `daq_move_plugins/daq_move_redpitaya_fpga.py`
- `daq_move_plugins/daq_move_elliptec.py`
- `daq_move_plugins/daq_move_maitai_laser.py`

#### Agent 3: Camera and Detection Systems Developer
**Environment ID:** `urashg-detection-dev`
**Responsibilities:**
- DAQ_2DViewer_PyVCAM camera plugin
- ROI selection and real-time integration
- Background subtraction and signal processing
- Data export and visualization

**Key Deliverables:**
- `daq_viewer_plugins/plugins_2D/daq_2dviewer_pyvcam.py`
- Camera calibration utilities
- Image processing pipelines

#### Agent 4: Integration and Testing Specialist
**Environment ID:** `urashg-integration-test`
**Responsibilities:**
- System integration testing
- Automated measurement workflows
- Example scripts and documentation
- Performance optimization

**Key Deliverables:**
- `examples/automated_rashg_scan.py`
- `examples/polarization_calibration.py`
- Integration test suite
- Performance benchmarks

#### Agent 5: Documentation and User Experience
**Environment ID:** `urashg-docs-ux`
**Responsibilities:**
- Comprehensive documentation
- Installation guides
- Troubleshooting documentation
- User tutorials and examples

**Key Deliverables:**
- `README.md`
- `docs/installation.md`
- `docs/user_guide.md`
- `docs/troubleshooting.md`

## Phase-Based Development Plan

### Phase 1: Foundation and Core Infrastructure (Weeks 1-2)

**Objectives:**
- Set up project structure and development environment
- Implement hardware abstraction layers
- Create basic plugin skeletons

**Agent Assignments:**
- **HAL Specialist**: Hardware abstraction layer development
- **Move Plugin Developer**: Basic plugin structure setup

**Deliverables:**
- Complete project structure
- Hardware communication libraries
- Plugin entry points configuration
- Basic unit tests

**Container-Use Workflow:**
```bash
# Initialize environments
container-use create urashg-hal-dev
container-use create urashg-move-plugins

# Monitor progress
container-use log urashg-hal-dev --follow
container-use log urashg-move-plugins --follow

# Review and merge work
git checkout urashg-hal-dev
git checkout urashg-move-plugins
```

### Phase 2: Plugin Implementation (Weeks 3-4)

**Objectives:**
- Implement core PyMoDAQ plugins
- Develop camera interface with ROI support
- Create laser and polarization control systems

**Agent Assignments:**
- **Move Plugin Developer**: Complete actuator plugins
- **Detection Developer**: Camera plugin with advanced features
- **HAL Specialist**: Hardware optimization and error handling

**Deliverables:**
- Functional DAQ_Move plugins for all hardware
- Complete camera plugin with ROI integration
- Hardware error handling and recovery
- Plugin configuration files

### Phase 3: Integration and Automation (Weeks 5-6)

**Objectives:**
- System integration testing
- Automated measurement workflows
- Performance optimization

**Agent Assignments:**
- **Integration Specialist**: End-to-end testing and optimization
- **Documentation Specialist**: User guides and examples
- **All Agents**: Bug fixes and refinements

**Deliverables:**
- Complete automated measurement scripts
- System integration tests
- Performance benchmarks
- User documentation

### Phase 4: Documentation and Release Preparation (Week 7)

**Objectives:**
- Comprehensive documentation
- Release preparation
- Community feedback integration

**Agent Assignments:**
- **Documentation Specialist**: Final documentation and tutorials
- **Integration Specialist**: Release testing and validation
- **All Agents**: Final polish and bug fixes

**Deliverables:**
- Release-ready package
- Complete documentation suite
- Installation and deployment guides
- Community feedback integration

## Technical Implementation Details

### Red Pitaya FPGA PID Control

**Direct Register Access Strategy:**
```python
# Memory-mapped register access at base address 0x40300000
PID_BASE_ADDRESS = 0x40300000
OFFSET_PID1_SETPOINT = 0x20
OFFSET_PID1_P_GAIN = 0x24
OFFSET_PID1_I_GAIN = 0x28
OFFSET_PID1_D_GAIN = 0x2C
```

**Plugin Features:**
- Dual-purpose DAQ_Move/DAQ_Viewer functionality
- Real-time PID parameter adjustment
- Error signal monitoring
- Hardware loop status feedback

### Thorlabs ELL14 Multi-Axis Control

**Implementation Approach:**
- Use `elliptec` Python library for communication
- Multi-axis plugin supporting 3 rotation mounts
- Polarization state presets and calibration
- Coordinated movement for complex polarization states

### Photometrics Prime BSI Camera Integration

**Advanced Features:**
- Hardware ROI for efficient data acquisition
- Real-time background subtraction
- Signal threshold detection
- Multiple export formats (2D images + 0D integrated intensity)

## Container-Use Integration Commands

### Environment Management

**Create Development Environments:**
```bash
# Create specialized environments for each agent
container-use create urashg-hal-dev --image python:3.9-slim
container-use create urashg-move-plugins --image python:3.9-slim
container-use create urashg-detection-dev --image python:3.9-slim
container-use create urashg-integration-test --image python:3.9-slim
container-use create urashg-docs-ux --image python:3.9-slim
```

**Monitor Agent Progress:**
```bash
# Real-time monitoring
container-use log urashg-hal-dev --follow
container-use log urashg-move-plugins --follow

# View command history
container-use log urashg-hal-dev --commands-only

# Check environment status
container-use status
```

**Review and Integration:**
```bash
# Checkout agent work for review
container-use checkout urashg-hal-dev

# Merge successful work
git checkout main
git merge urashg-hal-dev

# Clean up completed environments
container-use destroy urashg-hal-dev
```

### Development Environment Configuration

**Base Environment Setup:**
```dockerfile
# pymodaq-dev-environment
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    cmake \
    pkg-config \
    libhdf5-dev \
    libopencv-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

# Set working directory
WORKDIR /workspace
```

## Risk Mitigation and Contingency Plans

### Technical Risks

**1. FPGA Register Mapping Unknown**
- **Risk**: Difficulty determining precise register offsets
- **Mitigation**: Extract from Red Pitaya Verilog source code
- **Contingency**: Empirical determination via test scripts

**2. PyVCAM ROI Implementation Challenges**
- **Risk**: Limited ROI documentation in PyVCAM
- **Mitigation**: Use ctypes for direct PVCAM.dll access
- **Contingency**: Implement software ROI as fallback

**3. Multi-Device Timing Issues**
- **Risk**: Synchronization problems between hardware components
- **Mitigation**: PyMoDAQ's thread-safe communication patterns
- **Contingency**: Extensive integration testing with mock devices

### Development Risks

**1. Agent Coordination Challenges**
- **Risk**: Conflicts between agent work or dependencies
- **Mitigation**: Clear interface definitions and modular design
- **Container-Use Solution**: Isolated environments prevent conflicts

**2. Hardware Access Limitations**
- **Risk**: Limited access to physical hardware during development
- **Mitigation**: Extensive use of mock devices and simulators
- **Container-Use Solution**: Easy environment switching for hardware testing

## Success Metrics and Milestones

### Technical Milestones

**Week 2:** Hardware abstraction layers functional
**Week 4:** All plugins operational individually
**Week 6:** Complete system integration working
**Week 7:** Release-ready package with documentation

### Performance Targets

- **Laser Stabilization**: <1% power fluctuation
- **Camera Frame Rate**: >10 Hz for full frame, >50 Hz for ROI
- **Polarization Accuracy**: ±0.1° rotation precision
- **System Response Time**: <100ms for parameter changes

### Quality Metrics

- **Code Coverage**: >90% test coverage
- **Documentation**: 100% API documentation
- **User Experience**: Installation time <15 minutes
- **Reliability**: >99% uptime during extended measurements

## Future Extensions and Roadmap

### Phase 5: Advanced Features (Future)

**Galvo Mirror Integration:**
- Use `pymodaq_plugins_daqmx` for National Instruments DAQ
- 2D raster scanning capabilities
- Synchronized acquisition patterns

**Enhanced Analysis:**
- Real-time fitting algorithms
- Automated calibration routines
- Machine learning-based optimization

**Multi-Modal Integration:**
- Fluorescence lifetime imaging
- Transient absorption measurements
- Combined measurement modalities

### Community and Ecosystem Development

**Plugin Ecosystem:**
- Template for similar optical systems
- Community contribution guidelines
- Plugin validation and testing standards

**Educational Resources:**
- Tutorial series for μRASHG microscopy
- Hands-on workshops and training
- Academic collaboration partnerships

## Conclusion

This comprehensive plan leverages container-use's distributed development capabilities to create a robust, professional-grade PyMoDAQ plugin package for μRASHG microscopy. By assigning specialized agents to different components and maintaining isolated development environments, we can ensure rapid, high-quality development while minimizing integration risks.

The modular architecture ensures that each component can be developed, tested, and refined independently, while the container-use workflow provides transparency, control, and easy integration of successful work. This approach will deliver a production-ready plugin package that serves as a model for complex scientific instrument control systems.

---

**Remember to inform users about viewing work:**
- Use `container-use log <env_id>` to monitor agent progress
- Use `container-use checkout <env_id>` to review and integrate work
- Each environment maintains complete isolation until explicitly merged
