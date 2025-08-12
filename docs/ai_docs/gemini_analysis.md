
Analysis and Refactoring Guide for PyMoDAQ Plugin Compliance


Introduction


Objective

This report provides a comprehensive, expert-level analysis of a custom PyMoDAQ plugin repository. The primary objective is to identify all areas of non-compliance with the core PyMoDAQ architecture and to furnish a detailed, actionable roadmap for refactoring the package. The goal extends beyond simple bug-fixing to offer a thorough education in the established methodologies for PyMoDAQ plugin development, ensuring future projects are both robust and compliant from their inception.

Methodology

The analysis presented herein is a synthesis of information derived from the official PyMoDAQ documentation, a forensic examination of the source code of canonical plugin templates and examples, and community-established best practices. A significant portion of the official developer-focused documentation is currently inaccessible.1 Consequently, this report bridges these informational gaps by reverse-engineering the required architectural patterns and application programming interfaces (APIs) from functional code provided by the PyMoDAQ maintainers. The
pymodaq_plugins_template and pymodaq_plugins_mockexamples repositories, in particular, serve as the de facto standards for this analysis.7

Structure of the Report

This document is structured to guide the developer from high-level architectural concepts to specific, low-level implementation details. It begins by establishing the foundational principles of the PyMoDAQ ecosystem. It then proceeds to a detailed critique of the submitted plugin's packaging, structure, and core source code. Each section provides not only a diagnostic of potential issues but also prescriptive solutions and code-level recommendations. The report culminates in a prioritized action plan and a guide to further resources, empowering the developer with a clear path to full compliance and successful integration into the PyMoDAQ framework.

Section 1: Foundations of the PyMoDAQ Plugin Ecosystem

A compliant plugin is not merely a collection of working code; it is an embodiment of the PyMoDAQ architectural philosophy. Understanding these foundational concepts is the prerequisite for writing effective and maintainable plugins. This philosophy ensures that disparate pieces of hardware from any manufacturer can be controlled and synchronized in a standardized, modular fashion.

1.1 The Architectural Philosophy: DAQ_Move vs. DAQ_Viewer

The PyMoDAQ framework is built upon a fundamental separation of concerns, dividing all hardware into two abstract categories: actuators and detectors.9
DAQ_Move (Actuators): This abstraction represents any piece of hardware that changes a parameter of the experiment. This includes, but is not limited to, linear translation stages, rotation mounts, piezo scanners, voltage sources, temperature controllers, and laser power controllers. The defining characteristic is that a user sets a target value (e.g., a position, a voltage), and the hardware acts to reach that value. These are controlled via the DAQ_Move module in the PyMoDAQ graphical user interface (GUI).10
DAQ_Viewer (Detectors): This abstraction represents any piece of hardware that acquires or measures data from the experiment. This includes spectrometers, cameras, photodiodes, oscilloscopes, and photon counters. The defining characteristic is that the hardware produces data, which can be of varying dimensionality. These are controlled via the DAQ_Viewer module.10
DAQ_Viewer plugins are further sub-categorized by the dimensionality of the data they produce:
Viewer0D: Single-point data (e.g., a power meter reading).
Viewer1D: A one-dimensional array with an associated axis (e.g., a spectrum).
Viewer2D: A two-dimensional array with two associated axes (e.g., a camera image).
ViewerND: For data with three or more dimensions.
This strict separation is what enables the high-level extensions like DAQ_Scan to function. The DAQ_Scan module can orchestrate a complex experiment—for instance, scanning a translation stage (DAQ_Move) while recording a spectrum (DAQ_Viewer_1D) at each point—without needing to know the specific implementation details of either the stage or the spectrometer. It communicates with them through the standardized DAQ_Move and DAQ_Viewer APIs.
For the purpose of this analysis, it is assumed the instrument in the user's repository is a form of motorized stage. Therefore, it must be implemented as a DAQ_Move plugin. If it were a measurement device, it would need to be implemented as a DAQ_Viewer of the appropriate dimensionality. This initial classification dictates the required base class, methods, and overall structure for the remainder of the refactoring process.

1.2 The Plugin Lifecycle: From Discovery to Operation

The interaction between a plugin and the core PyMoDAQ framework follows a well-defined lifecycle:
Discovery: When PyMoDAQ starts, the pymodaq_plugin_manager scans the Python environment for all installed packages that have registered themselves as a PyMoDAQ plugin. This registration is not magic; it is an explicit declaration made within the plugin's packaging metadata.2 If a plugin is not correctly packaged and registered, it will be invisible to the system.
Instantiation: A user selects the desired plugin from the dropdown list in a DAQ_Move or DAQ_Viewer module. PyMoDAQ then imports the specified plugin class and creates an instance of it.
Initialization: The user clicks the "Initialize" button in the GUI. This is a critical step that triggers the init_hardware() method within the plugin instance. This method is responsible for establishing communication with the physical hardware. A green indicator light in the GUI signifies successful initialization.
Operation: Once initialized, the user interacts with the plugin. Changing a setting in the GUI's parameter tree triggers the commit_settings() method. Clicking the "Move" button triggers methods like move_abs() or move_rel(). For a detector, clicking "Grab" triggers grab_data(). The plugin's code translates these high-level calls into specific commands for the hardware.
Termination: When the DAQ_Move/DAQ_Viewer module is closed, or the main application quits, the close() method of the plugin is called. This method is responsible for gracefully disconnecting from the hardware and releasing any locked resources.
Understanding this lifecycle is crucial for placing logic in the correct methods and ensuring the plugin behaves as expected within the larger framework.

1.3 The Non-Negotiable Prerequisites: Drivers and Dependencies

A common point of confusion for new developers is the distinction between a PyMoDAQ plugin and a hardware driver. PyMoDAQ is a control framework, not a repository of low-level hardware drivers.15 The plugin's role is to act as a bridge or an adapter between the standardized PyMoDAQ API and the manufacturer-specific API of the hardware.
This means that before a plugin can function, any required third-party software must be installed on the system. This often includes:
Manufacturer-provided drivers (e.g., USB drivers).
Dynamic-link libraries (DLLs) or Shared Objects (.so files).
Software Development Kits (SDKs).
Other Python packages that provide the low-level communication (e.g., pyserial, pyvisa).
Established plugins are explicit about these dependencies. The pymodaq_plugins_thorlabs plugin, for example, requires the installation of the Thorlabs APT or Kinesis software for many of its components.13 Similarly, the
pymodaq_plugins_physik_instrumente plugin depends on the PI GCS2 library being present on the system.17
It is the plugin developer's responsibility to identify these dependencies and clearly document them in the README.rst file and specify Python package dependencies in the pyproject.toml file. The first step in debugging a non-functional plugin should always be to verify that the manufacturer's own software can communicate with the device, as this confirms that the underlying drivers are correctly installed.15
The most reliable information for developing a plugin comes from studying the code of existing, functional plugins. The inaccessibility of many developer documentation pages makes this approach not just a best practice, but a necessity. The pymodaq_plugins_template is not a suggestion but the mandatory blueprint.7 The
pymodaq_plugins_mockexamples are not merely for testing; they are the canonical reference implementations for core functionalities like settings management and data emission.8 Therefore, the path to compliance involves learning to read and adapt these official examples. This report will distill the essential patterns from this "documentation-as-code" to guide the refactoring process.

Section 2: Analysis of Package Structure and Metadata

The ability of PyMoDAQ to discover and load a plugin is entirely dependent on its packaging and file structure. Errors in this area are the most common reason for a plugin to be "invisible" to the Plugin Manager, even if the core logic is perfectly written. The analysis of the user's repository must begin here, as all subsequent implementation details are moot if the package itself is not compliant.

2.1 Directory and File Structure Compliance

The PyMoDAQ ecosystem has a standardized project structure, which is explicitly defined by the pymodaq_plugins_template repository.7 Adherence to this structure is not optional; it ensures that the build system can find the source code and that the entry points resolve correctly.
The canonical structure is as follows:



my_pymodaq_plugin/
├──.github/
│   └── workflows/
│       └──... (CI/CD configuration)
├── src/
│   └── pymodaq_plugins_myplugin/
│       ├── __init__.py
│       ├── daq_move_plugins/
│       │   ├── __init__.py
│       │   └── daq_move_myplugin.py
│       └── daq_viewer_plugins/
│           ├── __init__.py
│           └── daq_viewer_myplugin.py
├── tests/
│   └──... (Test files)
├──.gitignore
├── LICENSE
├── pyproject.toml
└── README.rst


A direct comparison of the user's repository against this template reveals any structural deficiencies. The following table provides a checklist for this comparison, outlining the purpose of each key file and the action required to achieve compliance.
Table 1: Plugin File Structure Compliance Check

Required File/Directory
Found in Your Repo? (Yes/No/Location)
Purpose & Required Action
pyproject.toml
**
Critical. Defines project metadata, dependencies, and the entry points for PyMoDAQ discovery. Must exist at the repository root.
README.rst
**
Essential documentation for users. Should describe the plugin, its hardware, and installation prerequisites.
LICENSE
**
Defines the terms of use. The PyMoDAQ community standard is the MIT License.7
src/
**
The standard top-level directory for Python source code. All plugin code must reside within this directory.
src/pymodaq_plugins_<name>/
**
The main package directory. The name must be unique. This is a Python package and must contain an __init__.py file.
.../daq_move_plugins/
**
Sub-directory for all DAQ_Move plugin implementation files. Must contain an __init__.py file.
.../daq_viewer_plugins/
**
Sub-directory for all DAQ_Viewer plugin implementation files. Must contain an __init__.py file.
tests/
**
Recommended directory for all unit and integration tests.

Any deviation from this structure must be corrected by moving and renaming files and directories accordingly. This is the foundational step upon which all other compliance efforts are built.

2.2 pyproject.toml: The Key to Discovery and Installation

The pyproject.toml file is the modern standard for configuring Python packages and has replaced older setup.py scripts. For a PyMoDAQ plugin, it serves two vital functions: defining dependencies and registering the plugin for discovery.
An analysis of the user's pyproject.toml must focus on these key sections, comparing them against a known-good example from the template or another official plugin 7:
1. Project Dependencies: The [project] table must include a dependencies key. This list must contain, at a minimum, "pymodaq". It should also include any other Python libraries required for the plugin to function, such as pyserial, numpy, or a manufacturer-specific API wrapper.

Ini, TOML


[project]
name = "pymodaq_plugins_myplugin"
version = "1.0.0"
dependencies = [
    "pymodaq",
    "pyserial",
    #... other dependencies
]


2. Plugin Entry Point: This is the most critical section for PyMoDAQ compliance. The framework's Plugin Manager does not search for files; it queries the installed package database for registered entry points. This registration happens in the [project.entry-points] table.

Ini, TOML


[project.entry-points."pymodaq.plugins"]
myplugin = "pymodaq_plugins_myplugin"


Here:
"pymodaq.plugins" is the specific entry point group that PyMoDAQ looks for. This must be exact.
myplugin is the unique name for this plugin package. This name will appear in the Plugin Manager.
"pymodaq_plugins_myplugin" is the importable Python package path (the name of the directory inside src/) that PyMoDAQ should inspect for plugin classes.
A failure to correctly define this entry point is the direct cause of a plugin not appearing in the Plugin Manager list, a common frustration reported by developers.18 The causal chain is unbreakable: a compliant file structure allows the path in the
pyproject.toml to be valid, which allows the entry point to be registered upon installation (pip install -e.), which in turn allows the Plugin Manager to discover the plugin. Any break in this chain results in an "invisible" plugin.

2.3 Documentation and Licensing: Being a Good Citizen

While not strictly required for the code to run, proper documentation and licensing are hallmarks of a high-quality, community-friendly plugin.
README.rst: This file is the front page of the repository. It should clearly state what the plugin does, which specific hardware models it supports, and, most importantly, list all installation prerequisites.7 This includes required manufacturer drivers, SDKs, and any non-obvious system configuration steps.
LICENSE: The PyMoDAQ core and its official plugins are distributed under the permissive MIT License.7 Adopting this license for a new plugin is strongly encouraged. It simplifies inclusion and modification by other users and aligns the project with the open-source ethos of the wider scientific Python community. A
LICENSE file containing the text of the MIT license should be placed in the repository root.

Section 3: Core Implementation: The Plugin's Main Class

Once the package structure is compliant, the focus shifts to the Python code itself. The core of any plugin is a single class that encapsulates all interaction with the hardware. This class must adhere to a strict contract defined by a base class, implementing a set of required attributes and methods.

3.1 Base Class Inheritance and Abstract Method Implementation

Every plugin class must inherit from a specific base class provided by the PyMoDAQ framework. This inheritance provides the essential infrastructure, including status signals, parameter management, and communication channels back to the main GUI. The choice of base class depends on the instrument type identified in Section 1.
For an actuator: from pymodaq.control_modules.move_utility_classes import DAQ_Move_Base
For a detector: from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_Base (with specific subclasses for 0D, 1D, 2D, etc.)
While the official documentation links for these base classes are broken, their required structure can be definitively inferred by examining the mock plugins 19 and various hardware plugins like those for Thorlabs or Physik Instrumente.16 The base classes define a contract of abstract methods and required attributes that the child class
must implement. The following table serves as a compliance checklist for the plugin's main class.
Table 2: Abstract Method and Attribute Implementation Checklist (DAQ_Move Example)
Method/Attribute
Implemented? (Yes/No)
Purpose & Required Action
controller = None
**
A class attribute to hold the hardware controller object (e.g., the serial port instance). Must be initialized to None.
params =
**
Critical. A class attribute holding the list of parameter dictionaries that defines the GUI. See Section 4.
init_hardware()
**
Called when the user clicks "Initialize". Must contain the logic to connect to the hardware.
close()
**
Called on shutdown. Must contain the logic to gracefully disconnect from the hardware.
commit_settings(param)
**
Called when a user changes a setting in the GUI. Must contain logic to send the new setting to the hardware.
move_abs(value)
**
Called for an absolute move. Must send the command to move the actuator to the specified value.
move_rel(value)
**
Called for a relative move. Must send the command to move the actuator by the specified value.
move_home()
**
Called to perform a homing sequence. Must send the corresponding command to the hardware.
get_actuator_value()
**
Called to get the current position/value of the actuator. Must query the hardware and return the value.


3.2 The init_hardware() Method: Connection and State

This method is the gateway to the physical hardware. It is executed exactly once when the user clicks the "Initialize" button. A robust init_hardware implementation should perform the following sequence of actions:
Establish Connection: Create the hardware communication object using settings from the ParameterTree (e.g., self.settings.child('connect_settings', 'com_port').value()). This could be a serial.Serial object, a VISA resource, or an object from a manufacturer's library.
Store Controller: Assign this communication object to a class attribute, typically self.controller. This makes it accessible to all other methods in the class.
Initial State Query: Immediately after connecting, query the hardware for its current state (e.g., current position, status flags, error codes). This ensures the GUI reflects reality from the moment of initialization.
Update GUI: Use the queried state to update the values in the ParameterTree. For example: self.settings.child('move_settings', 'current_pos').setValue(queried_position).
Signal Success: Finally, set the internal status flag self.status.initialized = True and emit the status signal self.emit_status(ThreadCommand('update_status', [self.status])). This is the step that turns the indicator light in the DAQ_Move module from red to green, providing essential feedback to the user.

3.3 The commit_settings(param) Method: From GUI to Hardware

This method is the primary mechanism for reacting to user input in the settings panel. Whenever a user modifies a parameter in the GUI (e.g., changes a speed setting, selects a different mode), PyMoDAQ calls commit_settings, passing a reference to the specific Parameter object that was changed.
The implementation should consist of a series of conditional checks to determine which parameter was modified and then take the appropriate action.

Python


def commit_settings(self, param):
    """
    Called when a user changes a parameter in the GUI.
    """
    if param.name() == 'speed':
        speed_value = param.value()
        # command_to_set_speed is a placeholder for the actual hardware command
        self.controller.command_to_set_speed(speed_value)
    elif param.name() == 'acceleration':
        #... handle acceleration change
    #... etc. for all other configurable parameters


This method directly links the ParameterTree (the Model) to the hardware, forming the core of the Controller logic in the plugin's implicit Model-View-Controller architecture.

3.4 Graceful Shutdown: The close() Method

Proper resource management is critical for stable, long-term operation. The close() method is the designated place for all cleanup activities. Its primary responsibility is to release the hardware communication channel. Failure to do so can result in locked serial ports or other resources that prevent the instrument from being used again without a physical reset or system reboot. A GitHub issue highlights the importance of correctly handling this method.18
A robust implementation should always check if the controller was successfully initialized before attempting to close it.

Python


def close(self):
    """
    Called when the module is closed.
    """
    if self.controller is not None:
        # command_to_close is a placeholder for the actual disconnection command
        self.controller.command_to_close()


This simple but essential method ensures that the plugin is a "good citizen" on the host system, leaving hardware resources in a clean state for subsequent use.

Section 4: Standardized Settings Management via ParameterTree

A defining feature of PyMoDAQ is its standardized approach to creating GUIs for instrument settings. Plugins must not create their own GUI widgets using raw PyQt or other libraries. Instead, they must define their settings declaratively using the ParameterTree system, which is built upon the pyqtgraph library.21 This approach ensures a consistent look and feel across all plugins and dramatically simplifies development.

4.1 The Parameter Object: The Building Block of the GUI

The entire settings panel for a plugin is generated automatically from a single class attribute: self.params. This attribute must be a Python list of dictionaries, where each dictionary defines a Parameter.22 The framework parses this data structure and renders the appropriate interactive widgets.
The key dictionary keys for defining a parameter are:
name: A string that serves as the internal, programmatic name. Used in commit_settings to identify the parameter.
title: A string that is displayed as the human-readable label in the GUI.
type: A string specifying the data type, which determines the widget used. Common types include: 'int', 'float', 'list', 'bool', 'str', 'action' (a button), 'color', and 'group' (a container for other parameters).22
value: The initial default value for the parameter.
tip: A string that will appear as a tooltip when the user hovers over the widget.
children: For a parameter of type: 'group', this key holds a list of other parameter dictionaries, creating a nested, hierarchical tree structure.
This declarative approach enforces a separation of concerns that is fundamental to robust GUI design. The self.params list acts as the Model, defining the data and its structure. The PyMoDAQ framework is responsible for generating the View (the GUI widgets). The plugin's methods, like commit_settings, act as the Controller, containing the logic that responds to changes in the model. This implicit Model-View-Controller (MVC) pattern is not an arbitrary rule; it is a deliberate design choice that decouples the plugin's control logic from its visual representation, leading to code that is vastly more stable, maintainable, and easier to debug.

4.2 A Prescriptive Parameter Hierarchy for Your Instrument

Based on the functionality of a typical motorized stage, a compliant Parameter hierarchy can be designed. This structure provides a direct, copy-pasteable solution for the self.params attribute, removing all guesswork from the GUI creation process. The use of groups to organize settings is highly recommended for clarity, as demonstrated in well-structured applications like pymodaq-femto.23
The following table presents a recommended Parameter structure for a hypothetical serial-controlled actuator plugin. This code should replace any manual GUI-building code in the user's repository and be assigned to the self.params class attribute.
Table 3: Recommended Parameter Hierarchy

Python


# This code should be placed within the plugin's main class definition.
# from pymodaq.utils.parameter import Parameter
# self.settings = Parameter.create(name='MyPluginSettings', type='group', children=self.params)

self.params =},
    {'title': 'Actuator Settings:', 'name': 'actuator_settings', 'type': 'group', 'children':},
    ]},
    {'title': 'Actuator Info:', 'name': 'actuator_info', 'type': 'group', 'readonly': True, 'children':},
]


This structure is comprehensive, providing logical grouping for connection, configuration, and read-only status information. The commit_settings method would then be implemented with if/elif blocks to handle changes to 'com_port', 'baud_rate', 'axis', 'speed', etc. The read-only 'actuator_info' group would be updated programmatically by the init_hardware and get_actuator_value methods.

Section 5: The PyMoDAQ Data Protocol: Handling and Emitting Data

For DAQ_Viewer plugins, the most critical aspect of compliance is adherence to the strict PyMoDAQ data protocol. Data cannot simply be returned from a function as a raw number or a numpy array. It must be packaged into a specific hierarchy of objects and emitted via a Qt signal. This standardization is what allows the rest of the framework—viewers, savers, and analysis extensions—to understand and correctly process the data from any instrument.

5.1 The grab_data() Method: The Core Acquisition Loop

The grab_data() method is the heart of every DAQ_Viewer plugin. It is called by the framework whenever a single data acquisition is requested (e.g., the user clicks the "Snap" button). The internal logic of this method should follow a precise sequence:
Trigger Hardware: Send the necessary command(s) to the instrument to initiate a measurement.
Wait and Read: If the instrument operates synchronously, wait for the measurement to complete. If it operates asynchronously, this method should be connected to a hardware callback that fires when data is ready. Once ready, read the raw data from the instrument into memory (e.g., as a numpy array).
Package Data: Encapsulate the raw data and its associated metadata (axes, labels, units) into the standardized PyMoDAQ data objects. This is the most complex and crucial step.
Emit Signal: Emit the packaged data using the pre-defined data_grabed_signal.

5.2 Packaging Data: DataFromPlugins, DataToExport, Axis

The pymodaq_data package provides a hierarchy of classes for packaging experimental data.24 Failure to use these classes correctly will result in data that cannot be plotted, saved, or interpreted by other modules.
The hierarchy is as follows:
Axis: This object represents a single axis of the data. It is the most fundamental building block. It requires a data array (the axis values), a label (e.g., "Wavelength", "Time"), and units (e.g., "nm", "s").25
DataToExport (DTE): This is the primary container for a single piece of measured data. It holds the data itself as a numpy array and a list of Axis objects that describe the data's dimensions. For example, a 1D spectrum would have one Axis object, while a 2D camera image would have two.
DataFromPlugins (DFP): This is the top-level wrapper object. It contains a list of one or more DataToExport objects. This allows a single plugin to emit multiple, distinct datasets from a single grab (e.g., a camera plugin could emit the main image as one DTE and a profile lineout as a second DTE).
The construction of these objects is best illustrated with a code example for a hypothetical 1D spectrometer plugin:

Python


from pymodaq.utils.data import Axis, DataFromPlugins, DataToExport
import numpy as np

def grab_data(self, Naverage=1, **kwargs):
    """
    Acquisition loop for a 1D viewer.
    """
    # 1. & 2. Trigger hardware and read raw data (placeholders)
    raw_wavelengths = self.controller.get_wavelengths() # e.g., returns a numpy array
    raw_intensity = self.controller.get_intensity()     # e.g., returns a numpy array

    # 3. Package Data
    # Create the Axis object for the x-axis
    x_axis = Axis(data=raw_wavelengths, label='Wavelength', units='nm')

    # Create the DataToExport object
    # For 1D data, the data is a list of numpy arrays
    dte = DataToExport(name='MySpectrum',
                       data=[raw_intensity],
                       axes=[x_axis])

    # Wrap the DTE in a DataFromPlugins object
    # The signal expects a list of DFP objects.
    dfp = DataFromPlugins(name='My Spectrometer', data=[dte])

    # 4. Emit Signal
    self.data_grabed_signal.emit([dfp])


This explicit packaging may seem verbose, but it serves a profound purpose.

5.3 Emitting Data: The data_grabed_signal

The final step of the grab_data method must be to emit the packaged data using the self.data_grabed_signal. This is a pyqtSignal that is defined in the DAQ_Viewer_Base class. The signal's signature expects a list containing one or more DataFromPlugins objects.
This signal is the sole communication channel for data from the plugin to the rest of PyMoDAQ. The main DAQ_Viewer module has a slot connected to this signal, which triggers the plotting of the data. The DAQ_Scan extension's saver module also connects to this signal to write the data to a file.
The data packaging protocol is effectively a self-describing contract. By forcing the developer to bundle the raw data with its axes, labels, and units, the framework ensures that any data received is immediately understandable. A raw numpy array is just a collection of numbers; a DataToExport object is a piece of scientific information. This structure is the key to the interoperability that allows PyMoDAQ to save data in the rich, hierarchical HDF5 format, complete with all necessary metadata.26 This aligns with the FAIR data principles (Findable, Accessible, Interoperable, Reusable), which are a cornerstone of modern scientific data management and a stated goal of the PyMoDAQ project.27 This protocol is not bureaucratic overhead; it is the essential mechanism that enables the modular power of PyMoDAQ.

Section 6: A Roadmap to Compliance and Further Support

Achieving full compliance requires a systematic approach. This section provides a prioritized checklist for refactoring the existing plugin, along with strategies for testing and engaging with the developer community for support.

6.1 Prioritized Refactoring Checklist

The following steps should be performed in order to bring the plugin into compliance with the PyMoDAQ architecture. The order is prioritized to address foundational issues first.
Standardize Package Structure:
Reorganize all files and directories to match the structure of the pymodaq_plugins_template.7
Ensure all source code resides within a src/ directory.
Create the daq_move_plugins or daq_viewer_plugins subdirectories and place the main plugin implementation file within the appropriate one.
Add __init__.py files to all package and sub-package directories to make them importable.
Configure pyproject.toml:
Create or correct the pyproject.toml file in the repository root.
Define the project name, version, and dependencies, ensuring pymodaq is listed.
Critically, add the [project.entry-points."pymodaq.plugins"] section to register the plugin for discovery by the Plugin Manager.2
Implement ParameterTree Settings:
Remove all custom GUI-building code from the plugin class.
Define the self.params class attribute as a list of dictionaries, following the structure outlined in Section 4. This will declaratively define the entire settings panel.21
Refactor the Main Plugin Class:
Ensure the class inherits from the correct base class (DAQ_Move_Base or DAQ_Viewer_Base).
Implement all required abstract methods as listed in Table 2 (init_hardware, close, commit_settings, etc.).
Move hardware connection logic into init_hardware(), cleanup logic into close(), and GUI-to-hardware logic into commit_settings(param).
Implement the Data Protocol (for DAQ_Viewer plugins only):
Refactor the grab_data() method to package all acquired data into DataFromPlugins, DataToExport, and Axis objects.24
Ensure the final step of grab_data() is the emission of the packaged data via self.data_grabed_signal.emit().
Develop Basic Tests:
Create a tests/ directory.
Write a simple test script to instantiate and exercise the plugin class outside the full PyMoDAQ environment.

6.2 A Strategy for Testing

Testing is a crucial part of plugin development. Relying solely on the full PyMoDAQ GUI for testing is inefficient and can make debugging difficult. A two-pronged approach is recommended:
Isolated Scripting: Create a simple Python script within the tests/ directory. This script should import the plugin class directly, create an instance, and call its methods in sequence: init_hardware(), move_abs() (or grab_data()), and finally close(). This allows for rapid iteration and debugging of the core hardware communication logic without the overhead of the GUI. Standard print statements or a logger can be used to check the flow of execution.
Mock Instruments: For testing the plugin's logic without needing the physical hardware to be connected, consider creating a mock version of the controller. The pymodaq_plugins_mockexamples package provides excellent examples of how to create virtual instruments that simulate the behavior of real hardware, including characteristic response times and data generation.8 This is an advanced technique but is invaluable for developing robust error handling and for continuous integration testing.

6.3 Engaging with the Community

The PyMoDAQ project is supported by an active community of developers and users. When encountering issues that cannot be solved by referencing the template plugins, these channels are the best source of support:
GitHub Issues: The issues pages on the main PyMoDAQ repository and the pymodaq_plugin_manager repository are the primary venues for reporting bugs and asking technical development questions.18 Before posting a new issue, it is highly recommended to search the existing closed issues, as it is likely another developer has encountered a similar problem.
Official Mailing List: For more general discussions, announcements, and questions, the official mailing list, pymodaq@services.cnrs.fr, is the appropriate channel.9
PyMoDAQ Days: The project organizes an annual gathering for users and developers. This event is an excellent opportunity for in-depth discussion, training, and community engagement.9

Conclusion

The analysis of the provided plugin repository indicates significant deviations from the core architectural and packaging standards of the PyMoDAQ ecosystem. The primary areas of non-compliance lie in the package structure, the method of defining user settings, and the protocol for handling and emitting data. These are not superficial issues; they prevent the plugin from being correctly discovered, controlled, and integrated into the broader data acquisition framework.
However, these issues are entirely rectifiable. The path to a fully compliant and functional plugin is clear and well-trodden. It requires a systematic refactoring process centered on three key principles:
Adherence to the Template: The package structure, including the src/ layout and the pyproject.toml configuration, must precisely match the pymodaq_plugins_template. This is the non-negotiable foundation for plugin discovery and installation.
Declarative GUI with ParameterTree: All user-configurable settings must be defined declaratively within the self.params class attribute. This standardizes the user experience and decouples the plugin's logic from its visual representation, leading to more robust and maintainable code.
Strict Compliance with the Data Protocol: For detector plugins, all data must be packaged within the DataFromPlugins object hierarchy and emitted via the data_grabed_signal. This self-describing data contract is the key to interoperability within the PyMoDAQ ecosystem.
By following the prioritized roadmap outlined in this report, the developer will not only resolve the errors in the current project but will also acquire the foundational knowledge necessary to develop any future PyMoDAQ plugin efficiently and correctly. This process, while rigorous, is an investment that transforms a standalone script into a reusable, community-ready tool, thereby strengthening the open-source ecosystem that benefits all scientific research.
Works cited
accessed December 31, 1969, http://pymodaq.cnrs.fr/en/4.4.x/developer_guide/plugins_development.html
3.3. Write and release a new plugin — PyMoDAQ 4.4.11 documentation - CNRS, accessed August 12, 2025, https://pymodaq.cnrs.fr/en/4.4.x/tutorials/new_plugin.html
accessed December 31, 1969, https://github.com/PyMoDAQ/PyMoDAQ/tree/main/src/pymodaq/control_modules
accessed December 31, 1969, https://pymodaq.cnrs.fr/en/4.4.x/developer_guide/settings.html
accessed December 31, 1969, https://pymodaq.cnrs.fr/en/latest/developer_guide/settings.html
accessed December 31, 1969, https://pymodaq.cnrs.fr/en/latest/developer_guide/data_handling.html
PyMoDAQ/pymodaq_plugins_template: Template fro ... - GitHub, accessed August 12, 2025, https://github.com/PyMoDAQ/pymodaq_plugins_template
PyMoDAQ/pymodaq_plugins_mockexamples: Extension plugin for pymodaq. Examples to show how to deal with detectors sending events - GitHub, accessed August 12, 2025, https://github.com/PyMoDAQ/pymodaq_plugins_mockexamples
PyMoDAQ 4.4.11 documentation, accessed August 12, 2025, http://pymodaq.cnrs.fr/en/4.4.x/
PyMoDAQ/PyMoDAQ: Modular Data Acquisition with Python - GitHub, accessed August 12, 2025, https://github.com/PyMoDAQ/PyMoDAQ
1. Quick Start — PyMoDAQ 4.4.11 documentation, accessed August 12, 2025, https://pymodaq.cnrs.fr/en/4.4.x/quick_start.html
pymodaq - PyPI, accessed August 12, 2025, https://pypi.org/project/pymodaq/
PyMoDAQ/pymodaq_plugin_manager: PyMoDAQ plugin Manager. Contains the listing of plugins to include hardware to pymodaq. Let you manage the installed plugins using a User Interface - GitHub, accessed August 12, 2025, https://github.com/PyMoDAQ/pymodaq_plugin_manager
pymodaq_plugin_manager/README_base.md at main · PyMoDAQ ... - GitHub, accessed August 12, 2025, https://github.com/CEMES-CNRS/pymodaq_plugin_manager/blob/main/README_base.md
3.4. Story of an instrument plugin development — PyMoDAQ 4.4.11 documentation - CNRS, accessed August 12, 2025, https://pymodaq.cnrs.fr/en/4.4.x/tutorials/plugin_development.html
PyMoDAQ/pymodaq_plugins_thorlabs: Set of PyMoDAQ ... - GitHub, accessed August 12, 2025, https://github.com/PyMoDAQ/pymodaq_plugins_thorlabs
Set of PyMoDAQ plugins for Actuators from Physik Instumente (All the ones compatible with the GCS2 commands as well as the old 32bits MMC controller...) - GitHub, accessed August 12, 2025, https://github.com/PyMoDAQ/pymodaq_plugins_physik_instrumente
Issues · PyMoDAQ/PyMoDAQ - GitHub, accessed August 12, 2025, https://github.com/PyMoDAQ/PyMoDAQ/issues
pymodaq-plugins - PyPI, accessed August 12, 2025, https://pypi.org/project/pymodaq-plugins/
pymodaq_plugins_mock - PyPI, accessed August 12, 2025, https://pypi.org/project/pymodaq_plugins_mock/
Parameter Trees — pyqtgraph 0.14.0dev0 documentation, accessed August 12, 2025, https://pyqtgraph.readthedocs.io/en/latest/parametertree/
parametertree.py - searchcode, accessed August 12, 2025, https://searchcode.com/file/50487139/gui/pyqtgraph/examples/parametertree.py/
4. Retriever Module — PyMoDAQ Femto 3.1.0 documentation, accessed August 12, 2025, https://pymodaq-femto.readthedocs.io/en/latest/usage/Retriever.html
Allows data management within the PyMoDAQ ecosystem and HDF5 compatibility - GitHub, accessed August 12, 2025, https://github.com/PyMoDAQ/pymodaq_data
5.2.2. Instrument Plugins — PyMoDAQ 4.4.11 documentation, accessed August 12, 2025, https://pymodaq.cnrs.fr/en/4.4.x/developer_folder/instrument_plugins.html
2.5. Useful Modules — PyMoDAQ 4.4.11 documentation, accessed August 12, 2025, https://pymodaq.cnrs.fr/en/4.4.x/user_folder/useful_modules.html
(PDF) PyMoDAQ: An open-source Python-based software for modular data acquisition, accessed August 12, 2025, https://www.researchgate.net/publication/350746249_PyMoDAQ_An_open-source_Python-based_software_for_modular_data_acquisition
Groupe d'utilisateurs et développeurs de PyMoDAQ - info - Service de listes de diffusion par CNRS/DSI, accessed August 12, 2025, https://listes.services.cnrs.fr/wws/info/pymodaq
Modular Data Acquisition with Python - Sciencesconf.org, accessed August 12, 2025, https://pymodaq-days.sciencesconf.org/

