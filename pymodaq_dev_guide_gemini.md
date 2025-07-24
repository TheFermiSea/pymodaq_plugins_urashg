
Development and Integration Plan for an Automated SHG Microscopy System using PyMoDAQ


Section 1: Introduction and Executive Summary


1.1 Project Mandate

This document presents a comprehensive development and integration plan for a state-of-the-art, automated Second-Harmonic Generation (SHG) microscopy system. It addresses the specific requirements for a modified experimental design and provides an exhaustive, actionable blueprint for its realization. The core objectives are twofold: first, to conduct a rigorous evaluation of Proportional-Integral-Derivative (PID) control strategies for laser power stabilization using a Red Pitaya device; and second, to detail the complete software architecture and modular component development required to orchestrate the entire experiment within the PyMoDAQ framework.

1.2 Experimental Context

The optical system under consideration is a sophisticated SHG microscope designed for polarization-resolved studies. The experimental path begins with a MaiTai laser, the output of which is passed through an Electro-Optic Modulator (EOM) for high-speed power control and stabilization. The EOM features an integrated polarizer, functioning as a variable attenuator. Following the EOM, a quarter-wave plate (QWP) and a half-wave plate (HWP), both mounted in Thorlabs ELL14 motorized rotation mounts, are used to generate arbitrary incident polarization states. The beam is then raster-scanned across the sample by a set of galvo mirrors. The resulting SHG signal is collected and passed through a final analysis stage, consisting of another HWP in an ELL14 mount and a linear polarizer, before being imaged onto a Photometrics Prime BSI sCMOS camera.

1.3 Core Technical Challenges

The successful automation of this setup hinges on overcoming two primary technical challenges. The first is the selection and implementation of a high-performance, low-latency PID feedback loop for stabilizing the laser power via the EOM. This requires a careful decision between leveraging a pre-built software environment for the Red Pitaya or developing a more direct, low-level interface to its on-board Field-Programmable Gate Array (FPGA). The second challenge is the integration of a heterogeneous collection of advanced scientific instruments—including the Red Pitaya, multiple motorized optics, and a scientific-grade camera—into a single, cohesive, and automated control system. This requires a robust and flexible software framework capable of managing complex, synchronized experimental sequences.

1.4 Executive Summary of Recommendations

Following a thorough analysis of the available technologies and the specific experimental goals, this report puts forth a clear set of strategic recommendations:
PID Control Implementation: It is recommended to use the Red Pitaya's native FPGA-based PID controller, accessed via direct memory-mapped registers. This approach is favored over high-level software packages like PyRpl to ensure maximum performance, maintain full system flexibility, and align with the modular philosophy of the PyMoDAQ framework.1
Control Architecture: A hierarchical control architecture is proposed. The fast laser stabilization feedback loop will operate autonomously and deterministically on the Red Pitaya's FPGA. The host PC, running PyMoDAQ, will exercise high-level supervisory control, such as adjusting the power setpoint of the hardware PID loop, without being involved in the time-critical feedback process itself.
Software Development: The development effort will focus on creating three bespoke, modular plugins for PyMoDAQ:
A dual-purpose DAQ_Move/DAQ_Viewer plugin for the Red Pitaya, providing control over PID parameters and monitoring of loop signals.
A multi-axis DAQ_Move plugin for the Thorlabs ELL14 rotation mounts, controlling all polarization optics from a single interface.
A DAQ_Viewer plugin for the Photometrics Prime BSI camera, handling image acquisition and on-the-fly data reduction via Region of Interest (ROI) integration.
This plan provides a complete roadmap, from architectural design to detailed software implementation, for creating a powerful, flexible, and fully automated SHG microscopy platform.

Section 2: System Architecture and Integration Framework


2.1 The PyMoDAQ Orchestration Philosophy

The foundation of the proposed control system is PyMoDAQ (Modular Data Acquisition with Python), a software framework designed specifically for the orchestration of complex scientific experiments.3 PyMoDAQ transcends simple data acquisition by providing a structured environment to synchronize and automate the actions of multiple, disparate hardware components.5 This philosophy is perfectly suited to the current project, which involves the coordinated control of laser power, polarization optics, and a camera detector.
The architecture of PyMoDAQ is inherently modular, built upon three core concepts that map directly to the components of a physical experiment 3:
The Dashboard: This is the central graphical user interface (GUI) and control panel. It serves as the environment where all hardware modules are initialized, configured, and managed. The Dashboard allows the user to build a virtual representation of the experimental setup and launch extensions for automated tasks.5
DAQ_Move Modules: These plugins represent the "actuators" of the experiment—any device that can be set to a specific value. In this setup, the EOM (via the Red Pitaya's PID setpoint) and the three motorized waveplates are actuators. Multiple DAQ_Move modules can be instantiated to control all variable parameters.4
DAQ_Viewer Modules: These plugins represent the "detectors" of the experiment—any device that provides a measurement. The primary detector here is the Photometrics Prime BSI camera. The DAQ_Viewer module handles data acquisition, processing, and visualization.3
By leveraging this structure, a robust and scalable control system can be built without requiring extensive, monolithic custom software. Each piece of hardware is controlled by its own dedicated plugin, promoting code reusability and simplifying maintenance.

2.2 Proposed System Architecture Diagram

The overall system architecture is designed to optimize performance and maintain modularity. It centers on a host PC running the PyMoDAQ application, which communicates with each hardware component over its native interface. A textual representation of the architectural block diagram is as follows:
Host PC:
Software: Python environment with PyMoDAQ and its dependencies.
Core PyMoDAQ Modules: Dashboard, DAQ_Scan extension, DAQ_PID extension (for supervisory control).
Custom Plugins: DAQ_Move_RedPitayaFPGA, DAQ_Move_Elliptec, DAQ_Viewer_PyVCAM.
Control and Data Pathways:
PC <-> Red Pitaya (via Ethernet): The PC sends high-level configuration commands (e.g., "set P-gain to 0.5," "set power setpoint to 100 mW"). The Red Pitaya executes the fast PID loop internally and can send back monitoring data (e.g., error signal value).
PC <-> Thorlabs ELL14 Mounts (via USB-to-Serial): The PC sends commands to set the angular position of each of the three waveplates.
PC <-> Photometrics Prime BSI (via USB 3.0 or PCIe): The PC sends commands to configure the camera (exposure, gain, ROI) and receives 2D image data frames.
The Laser Power Stabilization Loop:
A critical feature of this architecture is the delegation of the time-critical stabilization loop entirely to the hardware. This fast, local loop operates independently of the host PC's operating system, ensuring deterministic, high-bandwidth performance.
Signal Path: A portion of the laser beam is picked off by a beam sampler (assumed) after the EOM and directed to a fast photodiode (PD).
Feedback Execution:
The analog signal from the PD is fed into a Fast Analog Input on the Red Pitaya.
The on-board FPGA PID Controller digitizes this signal, calculates the error relative to a digital setpoint stored in an FPGA register, and computes the PID correction term in real-time.
The digital correction value is sent to a Fast Analog Output on the Red Pitaya.
This analog voltage drives the amplitude modulation input of the EOM Driver, closing the loop.
This design explicitly separates the high-speed feedback control (on the FPGA) from the low-speed experimental orchestration (on the PC), leveraging the strengths of each platform.

2.3 Data and Control Flow

The system's operation during a typical automated measurement illustrates the flow of information:
Initialization: The user launches the PyMoDAQ Dashboard and loads a preset configuration file, which initializes the plugins for the Red Pitaya, the ELL14 mounts, and the Prime BSI camera. The laser stabilization loop on the Red Pitaya is already running autonomously.
Control Flow (Automated Scan): The user configures a DAQ_Scan experiment, for example, to measure SHG intensity versus incident polarization angle.
The DAQ_Scan module iterates through a predefined set of angles.
At each step, it sends a command to the DAQ_Move_Elliptec plugin: "Move HWP1 to angle $ \theta_n $".
Once the move is complete, DAQ_Scan sends a command to the DAQ_Viewer_PyVCAM plugin: "Acquire one frame."
Data Flow:
The DAQ_Viewer_PyVCAM plugin triggers the Prime BSI camera.
The camera exposes and transfers a 2D image frame (as a NumPy array) to the host PC.
The plugin performs a data reduction step, such as integrating the pixel values within a predefined ROI to yield a single 0D intensity value.
This 0D value is packaged into a DataToExport object and sent back to the DAQ_Scan module.
DAQ_Scan plots the new data point on a live graph and appends the data to a hierarchical HDF5 file.
Hierarchical PID Control: Separately from the scan, the user can interact with the DAQ_Move_RedPitayaFPGA plugin to manually adjust the PID parameters or the laser power setpoint. This supervisory control does not interfere with the fast hardware loop but allows for high-level optimization of the system's stability. The PyMoDAQ DAQ_PID extension can even be used to automate this optimization, for instance, by treating the Red Pitaya's setpoint register as an actuator and the measured average power from the photodiode as a detector to find the optimal operating point. This hierarchical approach is a cornerstone of the proposed architecture, providing both high-speed performance and high-level flexibility.

Section 3: Red Pitaya PID Interface: Evaluation and Recommendation


3.1 Overview of Implementation Strategies

The Red Pitaya is a versatile platform whose power stems from its Zynq System-on-Chip (SoC), which combines a dual-core ARM processor with a programmable FPGA fabric.7 For implementing a high-performance PID controller, two primary strategies emerge: leveraging the comprehensive, pre-built PyRPL software suite, or developing a more direct interface to the native PID controller embedded in the standard Red Pitaya FPGA image. The choice between these two paths is not merely technical but represents a fundamental decision about the experimental control philosophy—whether to adopt a turnkey, application-specific solution or to build a flexible, modular component within a broader framework.

3.2 Analysis of PyRPL (Python Red Pitaya Lockbox)

PyRPL is a powerful, open-source software package developed specifically for digital feedback control in quantum optics experiments.9 It effectively transforms the Red Pitaya from a general-purpose measurement tool into a specialized "lockbox" instrument.
Capabilities: PyRPL provides an extensive suite of digital signal processing tools accessible through both a GUI and a high-level Python API.10 Its key feature for this application is the inclusion of four advanced PID controllers. These controllers are highly sophisticated, supporting up to fourth-order filters and integration with other PyRPL modules like demodulators (for Pound-Drever-Hall locking) and arbitrary waveform generators.10 The system also includes high-order Infinite Impulse Response (IIR) filters with up to 24 poles and zeros for precise signal shaping.10
Implementation: Using PyRPL involves installing the Python package and its dependencies on a host computer. Upon connection, PyRPL deploys its own custom FPGA bitstream to the Red Pitaya.12 This bitstream is based on an older, but stable, version of the official Red Pitaya software (v0.95).11
Strengths: The primary advantage of PyRPL is its turnkey nature. It provides a feature-rich, out-of-the-box solution for complex locking scenarios, backed by an active community and proven in numerous research labs.10
Weaknesses: The strength of PyRPL is also its main weakness in the context of this project. By loading its own monolithic FPGA design, it creates a "walled garden" ecosystem. This makes it difficult, if not impossible, to integrate other custom FPGA logic that might be needed for future experimental requirements (e.g., complex triggering for the galvo scanners or camera). The reliance on an older FPGA design base may also preclude the use of features or performance improvements available in the latest official Red Pitaya operating system releases. This lack of modularity and forward-compatibility presents a significant constraint for a custom-built, evolving experimental setup.

3.3 Analysis of Direct FPGA PID Control

The standard, official FPGA image provided by Red Pitaya for its operating system includes a built-in Multiple-Input Multiple-Output (MIMO) PID controller module.1 This module consists of four independent, standard PID controllers that can be configured and controlled directly from the processor side.
Capabilities: The native PID controller provides the essential P, I, and D parameter settings, along with an integrator reset control.1 The output of each PID is summed with the output of the arbitrary signal generator, providing a flexible signal path.14 The key capability is that the PID algorithm runs entirely within the FPGA fabric, guaranteeing deterministic, low-latency execution suitable for high-bandwidth feedback loops.1
Implementation: Control is achieved by reading from and writing to specific memory-mapped FPGA registers.1 The base address for the PID controller module in the FPGA memory map is
0x40300000.2 From a host PC or from a script running on the Red Pitaya's Linux OS, these registers can be accessed using the
mmap system call to map the physical memory device (/dev/mem) into the process's virtual address space.16 Python libraries like
PyRedPitaya offer a higher-level wrapper around this process, but direct use of Python's mmap and struct modules provides the most fundamental and transparent control.18
Strengths: This approach offers maximum performance and flexibility. Since it uses the standard Red Pitaya software stack, it benefits from the latest updates and ensures that the rest of the FPGA remains available for other custom logic. Developing a dedicated PyMoDAQ plugin based on this method creates a clean, modular, and reusable component that integrates seamlessly into the larger experimental control framework without imposing any external constraints.
Weaknesses: The primary drawback is a higher initial development effort. It requires a deeper understanding of the Red Pitaya's system architecture, including the FPGA register map. While the base address is known, the specific register offsets for the P, I, and D parameters for each of the four PID channels are not explicitly detailed in the top-level documentation and would need to be extracted from the open-source Verilog hardware description files on Red Pitaya's GitHub or determined empirically.8

3.4 Comparative Analysis and Recommendation

A direct comparison highlights the strategic trade-offs between the two approaches.

Criterion
PyRPL (Python Red Pitaya Lockbox)
Direct FPGA Register Access
Performance / Latency
High. FPGA-based execution ensures low latency for the core loop.10
High. Direct FPGA execution provides the maximum possible performance.1
Ease of Implementation
Low. A turnkey software package with a high-level API and GUI.11
High. Requires development of a custom wrapper to interface with memory-mapped registers.16
Flexibility / Customization
Low. Operates as a monolithic system with a custom FPGA image, limiting other uses.13
High. Works with the standard OS, leaving the FPGA open for other custom logic and future expansion.8
Required Expertise
Medium. Requires proficiency with the Python API and understanding the PyRPL ecosystem.11
High. Requires understanding of low-level concepts like memory mapping and FPGA register architecture.2
Ecosystem Integration
Poor. Creates a self-contained, isolated environment. Difficult to integrate into a broader, modular framework like PyMoDAQ.
Excellent. Enables the creation of a clean, dedicated PyMoDAQ plugin that is fully interoperable with other components.
Long-Term Maintainability
Medium. Dependent on the continued development and support of the open-source PyRPL project.12
High. Tied directly to the official Red Pitaya software releases, ensuring access to future updates and support.8

Recommendation: For the successful development of this versatile SHG microscopy platform, the Direct FPGA Register Access method is unequivocally recommended.
The rationale for this recommendation is rooted in the project's need for modularity and long-term flexibility. While PyRPL is an excellent tool for its specific purpose, adopting it would mean building the entire experiment around the constraints of its ecosystem. This would be contrary to the modular philosophy of PyMoDAQ. By choosing the direct access method, the development effort is focused on creating a bespoke, lightweight, and highly efficient PyMoDAQ plugin for the Red Pitaya's PID controller. This component will function as a well-behaved citizen within the larger control architecture, performing its dedicated task of laser stabilization without imposing any limitations on the rest of the system. This approach preserves the Red Pitaya as a general-purpose, multi-functional instrument and ensures the entire experimental setup remains adaptable to future scientific questions and hardware additions.

Section 4: Core Instrumentation Development Plan


4.1 MaiTai Laser Control

Components: Spectra-Physics MaiTai Ti:Sapphire Laser.40
Functionality: As the primary ultrafast light source for the SHG experiment, the MaiTai laser's key parameters must be under programmatic control. This includes setting the output wavelength to excite specific fluorophores or optimize the SHG process, and controlling the laser's internal safety shutter.43 The system also requires asynchronous monitoring of the laser's status, including its current wavelength, output power, and warm-up state, to ensure stable and repeatable experimental conditions.43
PyMoDAQ Integration: A dedicated PyMoDAQ plugin will be developed to provide comprehensive control and monitoring of the MaiTai laser. This plugin, DAQ_Move_MaiTai, will be implemented as a multi-purpose module. It will function as a DAQ_Move actuator with distinct axes for 'Wavelength' and 'Shutter' control. Concurrently, it will incorporate DAQ_Viewer capabilities through a background monitoring thread that continuously polls the laser for status updates, displaying them in the plugin's user interface for real-time feedback.3

4.2 Laser Power Stabilization Subsystem

Components: MaiTai Laser, Electro-Optic Modulator (EOM), a photodiode (PD) for signal monitoring, and the Red Pitaya.
Control Loop: The core of the stabilization system is a high-speed feedback loop executed on the Red Pitaya's FPGA. The analog signal from the photodiode, which is proportional to the laser power, will be connected to the Red Pitaya's Fast Analog Input 1 (IN1). The FPGA's internal PID controller will continuously compare this digitized value against a programmable digital setpoint. The resulting error signal is processed through the PID algorithm, and the calculated correction signal is sent to the Fast Analog Output 1 (OUT1). This analog voltage output directly drives the EOM's amplitude modulation input, adjusting the laser transmission to maintain a constant power level.20
PyMoDAQ Integration: A dedicated PyMoDAQ plugin (detailed in Section 5) will serve as the high-level user interface to this hardware loop. It will provide GUI controls to adjust the PID parameters ($ K_p $, $ K_i $, $ K_d $), modify the power setpoint, and enable or disable the loop. It will also read back the error signal and PID output value for real-time monitoring and diagnostics within the PyMoDAQ environment.

4.3 Polarization State Generation and Analysis

Components: Three Thorlabs ELL14 motorized rotation mounts, holding one QWP and two HWPs.
Functionality: This subsystem provides complete control over the polarization state of the laser beam. The combination of the QWP and the first HWP, positioned after the EOM, allows for the generation of any arbitrary polarization state (linear, circular, or elliptical) incident on the sample. The final HWP, placed in the collection path before the final polarizer and the detector, acts as a polarization analyzer. By rotating this analyzer, one can perform polarization-resolved SHG measurements, which are crucial for probing molecular orientation and symmetry.
PyMoDAQ Integration: A single, multi-axis DAQ_Move plugin will be developed to control all three ELL14 mounts. PyMoDAQ's architecture readily supports plugins that manage multiple independent axes.22 This plugin will expose three named axes (e.g., 'QWP_inc', 'HWP_inc', 'HWP_ana') to the user, allowing for independent or coordinated control of the polarization optics directly from the
Dashboard or an automated DAQ_Scan.

4.4 SHG Signal Acquisition

Components: Photometrics Prime BSI sCMOS camera.
Functionality: The Prime BSI camera is the primary detector for the experiment, responsible for imaging the weak SHG signal generated by the sample.23 Key features of this camera, such as its high quantum efficiency (95%) and low read noise, are essential for detecting faint signals.24 For quantitative analysis, the most important observable is often not the full image but the total signal intensity integrated over a specific Region of Interest (ROI) that corresponds to the illuminated spot on the sample.
PyMoDAQ Integration: A DAQ_Viewer plugin will be created to interface with the Prime BSI camera. This plugin will manage camera initialization, configuration of critical parameters like exposure time and gain, and, crucially, the definition of an ROI. During an acquisition sequence, the plugin's grab_data function will command the camera to capture a frame. It will then perform an on-the-fly data reduction by integrating the pixel counts within the user-defined ROI. The plugin will export both the full 2D image (for visual feedback) and the calculated 0D intensity value (for quantitative plotting and data logging) to the PyMoDAQ framework.5

4.5 Future Integration Path: Raster Scanning Control

Components: A pair of galvo mirrors for X-Y beam scanning.
Control Interface: Galvo scanner systems are commonly controlled via analog voltage signals, typically in the ±10 V range, for positioning.27 This control is often provided by a multi-channel Data Acquisition (DAQ) card, such as those from National Instruments.
PyMoDAQ Integration Plan: The integration of raster scanning is a straightforward future extension within the PyMoDAQ ecosystem. The existing pymodaq_plugins_daqmx plugin, which provides an interface to National Instruments DAQ cards, can be utilized.28 A
DAQ_Move module would be configured within the Dashboard to use two analog output channels of the NI-DAQ card as 'X' and 'Y' actuators. The DAQ_Scan module can then perform a 2D scan, systematically moving the laser spot across the sample by controlling the galvo positions while acquiring an SHG signal from the camera at each pixel. This demonstrates the power and scalability of the chosen architectural approach.

Section 5: Modular Software Implementation: PyMoDAQ Plugins and Wrappers

The heart of the software development effort lies in the creation of bespoke PyMoDAQ plugins for each major hardware subsystem. These plugins serve as the bridge between the high-level, user-friendly PyMoDAQ environment and the low-level control libraries or communication protocols of the instruments. The following table summarizes the planned development.
Instrument
PyMoDAQ Plugin Type
Proposed Plugin Name
Core Python Library/Method
Key Implementation Notes
MaiTai Laser
DAQ_Move / DAQ_Viewer
DAQ_Move_MaiTai
pyserial
Multi-axis control for wavelength and shutter via RS-232 serial commands. Asynchronous thread for status monitoring.
Red Pitaya PID
DAQ_Move / DAQ_Viewer
DAQ_Move_RedPitayaFPGA
mmap, struct
Direct memory-mapped access to FPGA registers for PID control and monitoring. Multi-axis for P, I, D, and Setpoint.
Thorlabs ELL14
DAQ_Move
DAQ_Move_Elliptec
elliptec
Multi-axis control for three separate rotation mounts, each on its own COM port.
Photometrics Prime BSI
DAQ_Viewer (2D)
DAQ_Viewer_PyVCAM
pyvcam
Wraps the official PyVCAM library. Implements ROI selection and on-the-fly intensity integration for data reduction.


5.1 DAQ_Move_MaiTai: Plugin for Spectra-Physics MaiTai Laser

This plugin will provide integrated control and monitoring for the Spectra-Physics MaiTai laser, a critical component of the experimental setup. It will manage both actuation (wavelength, shutter) and asynchronous status polling.
Core Logic: The plugin will interface with the MaiTai laser via its RS-232 serial port. It will leverage a standard Python library such as pyserial to establish communication and send/receive ASCII-based SCPI commands, as documented in the laser's user manual.43 All commands are terminated with a carriage return or line feed, and responses are terminated with a line feed.43
Actuator Functionality (DAQ_Move): The plugin will be configured as a multi-axis actuator, exposing two primary control axes to the PyMoDAQ Dashboard:
Wavelength: This axis will control the laser's output wavelength. The move_abs method will issue the WAVelength nnn command, where nnn is the target wavelength in nanometers.43
Shutter: This axis will control the internal shutter. The move_abs method will send SHUTter 1 to open the shutter and SHUTter 0 to close it.43
Asynchronous Monitoring (DAQ_Viewer features): To provide real-time status without blocking the main application thread, the plugin will implement a background worker thread. This thread will run a loop that periodically queries the laser's status.
The loop will send commands such as READ:POWer? to get the current output power, READ:WAVelength? to confirm the operating wavelength, and *STB? to get the overall system status byte.43
The returned values will be parsed and used to update corresponding display widgets within the plugin's settings tree, providing the user with continuous, asynchronous feedback on the laser's health and operational state.
Conceptual Code Snippet:
Python
# In DAQ_Move_MaiTai.py
import serial
import threading
import time
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
from pymodaq.utils.daq_utils import ThreadCommand

class DAQ_Move_MaiTai(DAQ_Move_base):
    """
    PyMoDAQ Plugin for Spectra-Physics MaiTai Laser.
    """
    #... PyMoDAQ boilerplate (settings, signals, etc.)...

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        self.controller = None
        self.monitoring_thread = None
        self.stop_thread_flag = threading.Event()

    def commit_settings(self, param):
        if param.name() == 'connect':
            self.controller = serial.Serial(self.settings.child('com_port').value(),
                                            baudrate=9600, timeout=1)
            self.start_monitoring()

    def move_abs(self, position):
        axis = self.settings.child('multiaxes', 'selected_axis').value()
        if axis == 'Wavelength':
            command = f"WAVelength {position}\r\n"
        elif axis == 'Shutter':
            command = f"SHUTter {int(position)}\r\n"

        self.controller.write(command.encode())
        # Wait for command to complete, potentially by polling status
        self.emit_status(ThreadCommand('move_abs_done', [position]))

    def get_actuator_value(self):
        axis = self.settings.child('multiaxes', 'selected_axis').value()
        if self.controller is None:
            return 0.0
        if axis == 'Wavelength':
            self.controller.write(b"READ:WAVelength?\r\n")
            response = self.controller.readline().decode().strip()
            return float(response)
        elif axis == 'Shutter':
            self.controller.write(b"SHUTter?\r\n")
            response = self.controller.readline().decode().strip()
            return int(response)
        return 0.0

    def start_monitoring(self):
        if self.monitoring_thread is None:
            self.stop_thread_flag.clear()
            self.monitoring_thread = threading.Thread(target=self.run_monitoring)
            self.monitoring_thread.start()

    def run_monitoring(self):
        while not self.stop_thread_flag.is_set():
            try:
                # Query power
                self.controller.write(b"READ:POWer?\r\n")
                power = self.controller.readline().decode().strip()
                # Update GUI element for power
                if power:
                    self.settings.child('status', 'power').setValue(float(power))

                # Query other parameters...
                time.sleep(1) # 1 second polling interval
            except (serial.SerialException, ValueError):
                break # Exit loop on error

    def stop_motion(self):
        # Not applicable for setting wavelength/shutter
        pass

    def close(self):
        self.stop_thread_flag.set()
        if self.monitoring_thread is not None:
            self.monitoring_thread.join()
        if self.controller is not None:
            self.controller.close()



5.2 DAQ_Move_RedPitayaFPGA: Plugin for Red Pitaya PID Control

This plugin will provide comprehensive control and monitoring of the Red Pitaya's onboard FPGA-based PID controller. It will be implemented as a dual-purpose plugin, acting as both a DAQ_Move module to set parameters and a DAQ_Viewer module to monitor signals.
Core Logic: The plugin's fundamental mechanism will be direct memory access. On initialization, it will use Python's mmap module to open the /dev/mem device on the Red Pitaya and map the FPGA's physical address space into its own process memory.17 Specifically, it will map the page containing the PID controller's register block, which starts at the physical address
0x40300000.2 This provides a direct, low-latency pointer to the hardware registers.
Actuator Functionality (DAQ_Move): The plugin will be configured as a multi-axis actuator. The self.settings tree in the PyMoDAQ interface will define several controllable axes: Setpoint, P_Gain, I_Gain, D_Gain, and an EOM_Offset (which would correspond to the DAC offset).
move_abs(self, position) Method: This core method is called by PyMoDAQ to set the value of an actuator. It will check which axis is currently selected in the GUI. Based on the axis, it will calculate the correct integer representation of the position value, pack it into a 32-bit word using struct.pack('<I', int_value), and write this binary data to the appropriate offset within the memory-mapped region. For example, writing to self.pid_regs would update the PID setpoint register on the FPGA. The specific offset values for each parameter will be determined from the Red Pitaya's open-source Verilog files.8
Viewer Functionality (DAQ_Viewer): The grab_data(self, Naverage, **kwargs) method will read the current values from the PID error signal and output signal registers within the mapped memory. It will then emit this data using PyMoDAQ's standard signaling mechanism, allowing the values to be plotted live in the GUI for real-time diagnostics.
Conceptual Code Snippet:
Python
# In DAQ_Move_RedPitayaFPGA.py
import os
import mmap
import struct
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base

# Placeholder constants to be determined from Verilog source
PID_BASE_ADDRESS = 0x40300000
PAGE_SIZE = 4096
OFFSET_PID1_SETPOINT = 0x20
OFFSET_PID1_P_GAIN = 0x24

class DAQ_Move_RedPitayaFPGA(DAQ_Move_base):
    """
    PyMoDAQ Plugin for Red Pitaya FPGA PID Controller.
    Assumes this code is run directly on the Red Pitaya.
    """
    #... PyMoDAQ boilerplate (settings, signals, etc.)...

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        self.mem_fd = os.open('/dev/mem', os.O_RDWR | os.O_SYNC)
        self.pid_regs = mmap.mmap(self.mem_fd, PAGE_SIZE, mmap.MAP_SHARED,
                                  mmap.PROT_READ | mmap.PROT_WRITE,
                                  offset=PID_BASE_ADDRESS)

    def commit_settings(self, param):
        # Called when a setting is changed in the GUI
        pass

    def move_abs(self, position):
        """ Move the actuator to the absolute target position. """
        axis_name = self.settings.child('multiaxes', 'selected_axis').value()

        # Convert float position to appropriate integer representation for the FPGA
        # This scaling factor is hardware-dependent and must be calibrated.
        int_value = self.convert_pos_to_int(position)
        packed_value = struct.pack('<I', int_value)

        if axis_name == 'Setpoint':
            self.pid_regs = packed_value
        elif axis_name == 'P_Gain':
            self.pid_regs = packed_value
        #... other axes...

        self.emit_status(ThreadCommand('move_abs_done', [position]))

    def get_actuator_value(self):
        """ Get the current value of the actuator. """
        #... read from the corresponding register...
        return current_position

    def stop_motion(self):
        """ Stop the actuator. """
        pass # Not applicable for setting register values



5.3 DAQ_Move_Elliptec: Plugin for Thorlabs ELL14 Mounts

This plugin will provide unified control over the three motorized rotation mounts used for polarization control.
Core Logic: The plugin will be built upon the third-party elliptec Python library, which provides a simple and effective API for communicating with these devices over a serial connection.29 The plugin will be designed as a multi-axis
DAQ_Move module.
Initialization: The __init__ method will initialize the plugin. The settings tree will allow the user to specify the COM port for each of the three ELL14 controllers. Upon committing these settings, the plugin will create a dictionary of elliptec.Controller objects and a corresponding dictionary of elliptec.Rotator objects, one for each physical device. It will then home each rotator to establish a reference position.30
move_abs(self, axis, value) Method: This method will use the axis name (e.g., 'HWP1') to look up the correct Rotator object from its internal dictionary. It will then call that object's set_angle(value) method to move the mount to the desired absolute angle.30
get_actuator_value(self) Method: This method will similarly select the correct Rotator object and call its get('position') method to query and return the current angular position.
Conceptual Code Snippet:
Python
# In DAQ_Move_Elliptec.py
import elliptec
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base

class DAQ_Move_Elliptec(DAQ_Move_base):
    #... PyMoDAQ boilerplate for multi-axis actuator...

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        self.controllers = {}
        self.rotators = {}

    def commit_settings(self, param):
        """Initialize controllers and rotators based on GUI settings."""
        if param.name() == 'connect':
            # Assume settings contain a list of axis_names and com_ports
            for axis_name, com_port in self.settings.child('connections').children():
                try:
                    self.controllers[axis_name] = elliptec.Controller(com_port)
                    self.rotators[axis_name] = elliptec.Rotator(self.controllers[axis_name])
                    self.rotators[axis_name].home()
                except Exception as e:
                    self.emit_status(ThreadCommand('status', [str(e)]))

    def move_abs(self, position):
        """Move the selected rotator to the specified angle."""
        axis_name = self.settings.child('multiaxes', 'selected_axis').value()
        if axis_name in self.rotators:
            self.rotators[axis_name].set_angle(position)
        self.emit_status(ThreadCommand('move_abs_done', [position]))

    def get_actuator_value(self):
        """Get the current angle of the selected rotator."""
        axis_name = self.settings.child('multiaxes', 'selected_axis').value()
        if axis_name in self.rotators:
            return self.rotators[axis_name].get('position')
        return 0.0



5.4 DAQ_Viewer_PyVCAM: Plugin for Photometrics Prime BSI

This plugin will manage the Prime BSI camera, handling everything from configuration to data acquisition and processing.
Core Logic: The plugin will be a 2D DAQ_Viewer that wraps the official PyVCAM Python library.26 The
__init__ method will perform the necessary camera initialization sequence: pvc.init_pvcam(), followed by cam = next(Camera.detect_camera()), and finally cam.open() to establish a connection with the first detected camera.26 The plugin's settings tree will provide user controls for essential parameters like 'Exposure Time', 'Gain', and a group for 'ROI' settings (X, Y, Width, Height).
Region of Interest (ROI) Implementation: A key task for this plugin is to manage the ROI. High-level PyVCAM examples do not explicitly demonstrate ROI configuration.26 However, the underlying PVCAM SDK, which
PyVCAM wraps, fully supports this functionality.31 The implementation strategy will be twofold:
Inspect PyVCAM: The first step is to programmatically inspect the cam object provided by PyVCAM for any methods or parameters related to ROI, such as cam.set_roi() or a settable parameter like cam.roi = [x, y, w, h]. Libraries like pylablib that also wrap PVCAM suggest that ROI is handled by a special method, separate from general attributes.33
Fallback to ctypes: If PyVCAM does not provide a direct Pythonic way to set the ROI, the plugin will use Python's built-in ctypes library to load the PVCAM.dll directly. It can then call the C function for setting an ROI (e.g., pl_set_roi) by defining its function prototype in Python. This is a robust fallback that guarantees access to the full capabilities of the camera's SDK.
grab_data(self, Naverage, **kwargs) Method: This method will be the workhorse of the plugin. It will call frame = self.cam.get_frame(exp_time=...) to acquire a single image.26 The returned
frame is a NumPy array. The plugin will then perform the data reduction: shg_signal = np.sum(frame[y:y+h, x:x+w]). Finally, it will emit a DataToExport object containing multiple data elements: the full 2D frame array for display in the viewer, and the calculated 0D shg_signal as a separate data channel. This allows DAQ_Scan to plot the integrated intensity as a function of the scanned actuator.

Section 6: Integrated Operation and Example Workflow

This section outlines a practical workflow for conducting an automated experiment using the fully integrated system. The scientific goal is to measure the SHG signal intensity as a function of the incident laser's linear polarization angle, a common technique for probing material anisotropy.

6.1 Experimental Goal

The objective is to acquire a polarization-dependent SHG curve. This involves rotating a half-wave plate (HWP1) to vary the angle of linear polarization incident on the sample and measuring the resulting SHG intensity at each angle.

6.2 PyMoDAQ Setup

The experiment begins by configuring the PyMoDAQ Dashboard:
Launch Dashboard: The main PyMoDAQ application is started.
Load Actuator: The DAQ_Move_Elliptec plugin is loaded. From its multiple axes, the 'HWP1' axis is selected for control.
Load Detector: The DAQ_Viewer_PyVCAM plugin is loaded. In its settings, the user defines an appropriate exposure time and gain, and specifies an ROI on the camera view that encompasses the SHG signal from the sample.
Launch Scan Extension: The DAQ_Scan extension is launched from the Dashboard. It automatically detects the initialized actuator and detector modules.

6.3 DAQ_Scan Configuration

Within the DAQ_Scan module's GUI, the automated measurement is configured:
Scan Type: A Scan1D is selected, as one parameter (polarization angle) is being varied.
Actuator Selection: The DAQ_Move_Elliptec module (specifically the 'HWP1' axis) is selected as the scan actuator. The scan parameters are defined: for example, a start angle of 0 degrees, a stop angle of 90 degrees, and 19 steps (a step size of 5 degrees).
Detector Selection: The DAQ_Viewer_PyVCAM module is selected as the detector. The user ensures that the 0D data channel corresponding to the integrated ROI intensity is chosen for logging.

6.4 Execution Flow Narrative

With the configuration complete, the user clicks the 'Start Scan' button, initiating the following automated sequence:
The DAQ_Scan module takes control of the experiment.
It sends the first command to the DAQ_Move_Elliptec plugin: "Move 'HWP1' axis to 0.0 degrees." The plugin translates this into the appropriate serial command for the ELL14 mount.
The DAQ_Scan module waits for the move_done signal from the actuator plugin.
Upon completion of the move, DAQ_Scan sends a command to the DAQ_Viewer_PyVCAM plugin: "Execute grab_data."
The camera plugin triggers an acquisition, receives the 2D image frame, calculates the integrated intensity over the predefined ROI, and returns this 0D value to DAQ_Scan.
DAQ_Scan plots the first data point (Intensity vs. Angle = 0.0) on its live data viewer. Simultaneously, it saves the raw 2D image and the calculated 0D value into a structured HDF5 file, along with all relevant metadata (actuator position, detector settings, timestamps).
The DAQ_Scan module commands the actuator to move to the next position (5.0 degrees), and steps 3-6 are repeated until the entire angular range has been scanned.
Throughout this process, the laser stabilization loop on the Red Pitaya runs continuously and autonomously in the background, ensuring that the incident power remains constant for each data point, thereby eliminating it as a source of experimental error.

6.5 Example Orchestration Script

While the GUI provides an intuitive way to run experiments, PyMoDAQ's true power lies in its scriptability for full "lights-out" automation. The following conceptual script illustrates how such an experiment could be launched programmatically:

Python


from pymodaq.core.daq_move.daq_move_controller import DAQ_Move
from pymodaq.core.daq_viewer.daq_viewer_controller import DAQ_Viewer
from pymodaq.core.daq_utils import daq_utils as utils
from pymodaq.dashboard import DashBoard

# 1. Initialize the Dashboard
# This would typically load a saved preset file defining all plugins and their settings.
app = utils.get_qapp()
dashboard = DashBoard(dockarea=None)
dashboard.load_preset('SHG_Polarization_Scan.xml')

# 2. Get handles to the specific modules from the dashboard
hwp1_actuator = dashboard.get_move_by_title('Elliptec_HWP1')
camera_detector = dashboard.get_viewer_by_title('PrimeBSI_Camera')

# 3. Get the DAQ_Scan extension
daq_scan = dashboard.extensions

# 4. Configure the scan programmatically
daq_scan.set_scan_type('Scan1D')
daq_scan.set_scan_axes(actuators=[hwp1_actuator],
                       scan_starts=,
                       scan_stops=,
                       scan_steps=)
daq_scan.set_detectors([camera_detector])

# 5. Run the scan
daq_scan.start_scan()

# The script can now wait for the scan to finish or perform other tasks.
#...
app.exec()


This script demonstrates the seamless transition from interactive setup to fully automated, repeatable scientific measurements, which is the ultimate goal of this development plan.

Section 7: Conclusion and Strategic Recommendations


7.1 Summary of the Development Plan

This report has detailed a comprehensive plan for the development and integration of a highly capable, automated SHG microscopy system. The architectural foundation is the PyMoDAQ framework, which provides a modular and scalable environment for experimental orchestration. Key strategic decisions have been justified, including the adoption of the Red Pitaya's native FPGA-based PID controller for optimal performance and flexibility in the laser stabilization loop. This choice enables a hierarchical control scheme where time-critical feedback is handled by dedicated hardware, while high-level sequencing and user interaction are managed by the host software. The development path is clearly defined, focusing on the creation of three specific, reusable PyMoDAQ plugins for the Red Pitaya, the Thorlabs ELL14 rotation mounts, and the Photometrics Prime BSI camera.

7.2 Implementation Roadmap

A phased approach is recommended to ensure a smooth and systematic implementation process, allowing for validation at each stage.
Phase 1: Component Validation (1-2 weeks): Before diving into PyMoDAQ plugin development, each critical hardware component should be controlled with a simple, standalone Python script.
Red Pitaya: Write a script that runs on the Red Pitaya to mmap the FPGA registers and successfully write/read values to/from the PID control block.
Thorlabs ELL14: Write a script to connect to a single ELL14 mount using the elliptec library and command it to move to specific angles.
Photometrics Prime BSI: Write a script using PyVCAM to connect to the camera, set the exposure, and acquire a single frame.
Phase 2: Plugin Development and Testing (3-4 weeks): With the basic hardware communication validated, the focus shifts to creating the PyMoDAQ plugins.
Implement the DAQ_Move_RedPitayaFPGA, DAQ_Move_Elliptec, and DAQ_Viewer_PyVCAM plugins as detailed in Section 5.
Utilize the pymodaq_plugins_mock package for initial development and GUI testing without needing constant access to the physical hardware.35
Test each plugin individually within the PyMoDAQ Dashboard to confirm its functionality and stability.
Phase 3: System Integration and First Experiments (1 week): The final phase involves bringing all the components together.
Load all developed plugins into the Dashboard.
Configure and execute the first integrated DAQ_Scan, such as the polarization-dependent SHG measurement described in Section 6.
Debug and refine the system based on the performance of the integrated experiment.

7.3 Risk Assessment and Mitigation

Risk: Difficulty in determining the precise register offsets for the Red Pitaya's FPGA PID controller.
Mitigation: The Red Pitaya project is open-source. The primary mitigation is to directly inspect the Verilog HDL source code for the PID module, which is available on the official Red Pitaya GitHub repository.8 The register definitions will be explicitly declared in these files. As a secondary measure, the Red Pitaya user forum and technical support can be consulted.37
Risk: The PyVCAM library does not provide a straightforward, documented method for setting a Region of Interest (ROI).
Mitigation: The mitigation strategy outlined in Section 5.3 should be followed. First, perform a thorough programmatic inspection of the pyvcam.Camera object to uncover any undocumented methods. If none are found, the robust fallback is to use Python's ctypes library to interface directly with the underlying PVCAM.dll and call the C-level function for setting the ROI, the prototype for which can be found in the PVCAM SDK header files.39

7.4 Future Enhancements

The proposed architecture is inherently scalable and provides a solid foundation for future enhancements. Once the core system is operational, several extensions can be readily implemented:
Automated Raster Scanning: As outlined in Section 4.4, integrating the galvo mirrors for automated 2D imaging can be achieved by adding a NI-DAQ card and using the existing pymodaq_plugins_daqmx plugin.28
Multi-Modal Imaging: The Red Pitaya possesses additional analog inputs and outputs. These could be used for other simultaneous measurements, such as fluorescence lifetime imaging or transient absorption, by developing corresponding PyMoDAQ plugins and synchronizing them within DAQ_Scan.
Advanced Feedback: The PyMoDAQ DAQ_PID extension could be used in more complex ways, for example, to stabilize the sample position by using features in the camera image as an error signal and piezo stage controllers as actuators.
By adhering to this development plan, a powerful, flexible, and robust automated microscopy platform can be realized, empowering advanced scientific research through efficient and reproducible data acquisition.
Works cited
Red Pitaya as a PID controller, accessed July 23, 2025, https://content.redpitaya.com/blog/red-pitaya-as-a-pid-controller
Project - v0.94 — Red Pitaya 2.05-37 documentation, accessed July 23, 2025, https://redpitaya.readthedocs.io/en/latest/developerGuide/software/build/fpga/regset/in_dev/v0.94.html
PyMoDAQ: Navigating the Future of Data Acquisition - Scientia, accessed July 23, 2025, https://www.scientia.global/wp-content/uploads/Sebastian-Weber_V1.pdf
(PDF) PyMoDAQ: An open-source Python-based software for modular data acquisition, accessed July 23, 2025, https://www.researchgate.net/publication/350746249_PyMoDAQ_An_open-source_Python-based_software_for_modular_data_acquisition
PyMoDAQ/PyMoDAQ: Modular Data Acquisition with Python - GitHub, accessed July 23, 2025, https://github.com/PyMoDAQ/PyMoDAQ
PyMoDAQ in two minutes! - YouTube, accessed July 23, 2025, https://www.youtube.com/watch?v=PWuZggs_HwM
Red Pitaya User Manual, accessed July 23, 2025, https://docs.rs-online.com/84d1/0900766b8132f2ff.pdf
FPGA - Red Pitaya, accessed July 23, 2025, https://redpitaya.com/applications-measurement-tool/fpga/
Photonics - Red Pitaya, accessed July 23, 2025, https://redpitaya.com/pro/photonics/
PyRPL – Open-Source FPGA-Controlled Software for Quantum Optics, accessed July 23, 2025, https://content.redpitaya.com/blog/pyrpl-open-source-fpga-controlled-software-for-quantum-optics
What is PyRPL? — pyrpl 0.9.4.0 documentation, accessed July 23, 2025, https://pyrpl.readthedocs.io/
pyrpl-fpga/pyrpl: pyrpl turns your RedPitaya into a powerful DSP device, especially suitable as a lockbox in quantum optics experiments. - GitHub, accessed July 23, 2025, https://github.com/pyrpl-fpga/pyrpl
Quickstart Tutorial for PyRPL - Read the Docs, accessed July 23, 2025, https://pyrpl.readthedocs.io/en/latest/user_guide/tutorial/
PID controller — Red Pitaya 2.05-37 documentation, accessed July 23, 2025, https://redpitaya.readthedocs.io/en/latest/appsFeatures/applications/marketplace/pid.html
Documentation/appsFeatures/applications/marketplace/pid.rst at master - GitHub, accessed July 23, 2025, https://github.com/RedPitaya/Documentation/blob/master/appsFeatures/applications/marketplace/pid.rst
Sending an input to the FPGA - Redpitaya Forum, accessed July 23, 2025, https://forum.redpitaya.com/viewtopic.php?t=1675
mmap — Memory-mapped file support — Python 3.13.5 documentation, accessed July 23, 2025, https://docs.python.org/3/library/mmap.html
clade/PyRedPitaya - GitHub, accessed July 23, 2025, https://github.com/clade/PyRedPitaya
Accessing PL from the Python code - Redpitaya Forum, accessed July 23, 2025, https://forum.redpitaya.com/viewtopic.php?t=1377
electro-optic modulators – EOM, Pockels cells, phase modulator, amplitude, polarization, resonant, broadband, plasmonic - RP Photonics, accessed July 23, 2025, https://www.rp-photonics.com/electro_optic_modulators.html
Electro Optic Modulators | MEETOPTICS Academy, accessed July 23, 2025, https://www.meetoptics.com/academy/electro-optic-modulators
PyMoDAQ/pymodaq_plugin_manager: PyMoDAQ plugin Manager. Contains the listing of plugins to include hardware to pymodaq. Let you manage the installed plugins using a User Interface - GitHub, accessed July 23, 2025, https://github.com/PyMoDAQ/pymodaq_plugin_manager
Photometrics Prime BSI Scientific CMOS Camera - Scientifica - UK.COM, accessed July 23, 2025, https://www.scientifica.uk.com/products/photometrics-prime-bsi-scientific-cmos-camera
High Resolution BSI Scientific CMOS, accessed July 23, 2025, https://www.biovis.com/images/cameras/PrimeBSI-Datasheet.pdf
Photometrics Prime BSI Express | Cairn Research Ltd, accessed July 23, 2025, https://cairn-research.co.uk/product/photometrics-prime-bsi-express/
Photometrics/PyVCAM: Python3.X wrapper for ... - GitHub, accessed July 23, 2025, https://github.com/Photometrics/PyVCAM
Galvo-Resonant Scanners and Controllers - Thorlabs, accessed July 23, 2025, https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=11579
Welcome to pymodaq_plugins_daqmx's documentation! - GitHub Pages, accessed July 23, 2025, https://pymodaq.github.io/pymodaq_plugins_daqmx/
Simple control of Thorlabs Elliptec devices from Python. - GitHub, accessed July 23, 2025, https://github.com/roesel/elliptec
Elliptec: Simple control of Thorlabs Elliptec devices — elliptec 0.0.1 ..., accessed July 23, 2025, https://elliptec.readthedocs.io/
PVCAM 2.7 User Manual - NSTX-U, accessed July 23, 2025, https://nstx.pppl.gov/DragNDrop/Operations/Diagnostics_&_Support_Sys/VIPS/PVCAM%202.7%20Software%20User%20Manual.pdf
Software and Driver Downloads - Teledyne Photometrics, accessed July 23, 2025, https://testbook.photometrics.com/support/software-and-drivers
Photometrics PVCAM cameras — pylablib 1.4.3 documentation - Read the Docs, accessed July 23, 2025, https://pylablib.readthedocs.io/en/latest/devices/Pvcam.html
pyLabLib/docs/devices/Pvcam.rst at main - GitHub, accessed July 23, 2025, https://github.com/AlexShkarin/pyLabLib/blob/main/docs/devices/Pvcam.rst
List of Mock hardware plugins to use with PyMoDAQ - GitHub, accessed July 23, 2025, https://github.com/PyMoDAQ/pymodaq_plugins_mock
PyMoDAQ/pymodaq_plugins_mockexamples: Extension plugin for pymodaq. Examples to show how to deal with detectors sending events - GitHub, accessed July 23, 2025, https://github.com/PyMoDAQ/pymodaq_plugins_mockexamples
Implementation of digital computation (curve fitting) followed by PID control, accessed July 23, 2025, https://forum.redpitaya.com/viewtopic.php?t=22852
Where to find Red Pitaya's FPGA memory map exact pin addresses? - Redpitaya Forum, accessed July 23, 2025, https://forum.redpitaya.com/viewtopic.php?t=25362
PVCAM SDK & Driver | Teledyne Vision Solutions, accessed July 23, 2025, https://www.teledynevisionsolutions.com/products/pvcam-sdk-amp-driver?vertical=tvs-princeton-instruments&segment=tvs
Mai tai laser, by Spectra-Physics - Product details - Pubcompare, accessed July 23, 2025, https://www.pubcompare.ai/product/vyXhCZIBPBHhf-iF7gXr/
Mai tai ultrafast ti sapphire laser, by Spectra-Physics - Product details - Pubcompare, accessed July 23, 2025, https://www.pubcompare.ai/product/yFCvNZcByx5TsEHUlP49/
Mai Tai ® One Box Ti:Sapphire Ultrafast Lasers - Spectra-Physics, accessed July 23, 2025, https://www.spectra-physics.com/en/f/mai-tai-ultrafast-laser
Mai Tai - Spectra-Physics, accessed July 23, 2025, https://www.spectra-physics.com/medias/sys_master/spresources/h7f/h34/9954750398494/315A%20Rev%20A%20Mai%20Tai%20WB%20Users%20Manual/315A-Rev-A-Mai-Tai-WB-Users-Manual.pdf
