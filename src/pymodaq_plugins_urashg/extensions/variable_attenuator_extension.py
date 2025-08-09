# -*- coding: utf-8 -*-
"""
μRASHG Variable Attenuator Calibration Extension for PyMoDAQ

This extension provides a PyMoDAQ-compliant wrapper for the variable attenuator calibration experiment.
It allows the experiment to be discovered and launched from the PyMoDAQ dashboard.
"""

import logging
from pathlib import Path

from pymodaq_gui.utils.custom_app import CustomApp

from ..experiments.variable_attenuator_calibration import VariableAttenuatorCalibrationExperiment

logger = logging.getLogger(__name__)


class URASHG_Variable_Attenuator(CustomApp):
    """
    PyMoDAQ extension for μRASHG variable attenuator calibration experiment.
    
    This extension provides continuous power control via polarization attenuation
    with wide dynamic range and wavelength compensation.
    """
    
    # Extension metadata
    name = 'μRASHG Variable Attenuator Calibration'
    description = 'Variable power control via polarization attenuation'
    author = 'PyMoDAQ μRASHG Team'
    version = '1.0.0'
    
    def __init__(self, dashboard):
        """
        Initialize the Variable Attenuator calibration extension.
        
        Args:
            dashboard: PyMoDAQ dashboard instance
        """
        super().__init__(dashboard)
        self.dashboard = dashboard
        self.experiment = None
        
        logger.info(f"Initialized {self.name} extension")
    
    def setup_docks(self):
        """Set up the dock layout for the experiment."""
        # The experiment will handle its own dock setup
        pass
    
    def setup_menu(self):
        """Set up the menu for the experiment."""
        # Experiment controls are handled in the experiment GUI
        pass
    
    def start_extension(self):
        """Start the Variable Attenuator calibration experiment."""
        try:
            # Create the experiment instance
            self.experiment = VariableAttenuatorCalibrationExperiment(dashboard=self.dashboard)
            
            # Initialize and show the experiment GUI
            main_widget = self.experiment.ensure_gui_initialized()
            main_widget.show()
            
            logger.info("Started Variable Attenuator calibration experiment")
            
        except Exception as e:
            logger.error(f"Failed to start Variable Attenuator calibration experiment: {e}")
            raise
    
    def stop_extension(self):
        """Stop the Variable Attenuator calibration experiment."""
        try:
            if self.experiment:
                self.experiment.cleanup()
                self.experiment = None
            
            logger.info("Stopped Variable Attenuator calibration experiment")
            
        except Exception as e:
            logger.error(f"Failed to stop Variable Attenuator calibration experiment: {e}")
    
    def get_widget(self):
        """Get the main widget for the experiment."""
        if self.experiment:
            return self.experiment.main_widget
        return None


# Export for PyMoDAQ discovery
__all__ = ['URASHG_Variable_Attenuator']