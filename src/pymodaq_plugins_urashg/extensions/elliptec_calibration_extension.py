# -*- coding: utf-8 -*-
"""
μRASHG Elliptec Calibration Extension for PyMoDAQ

This extension provides a PyMoDAQ-compliant wrapper for the Elliptec rotator calibration experiment.
It allows the experiment to be discovered and launched from the PyMoDAQ dashboard.
"""

import logging
from pathlib import Path

from pymodaq_gui.utils.custom_app import CustomApp

from ..experiments.elliptec_calibration import ElliptecCalibrationExperiment

logger = logging.getLogger(__name__)


class URASHG_Elliptec_Calibration(CustomApp):
    """
    PyMoDAQ extension for μRASHG Elliptec rotator calibration experiment.
    
    This extension provides multi-rotator polarization control calibration
    with Malus law fitting and wavelength compensation.
    """
    
    # Extension metadata
    name = 'μRASHG Elliptec Calibration'
    description = 'Multi-rotator polarization control calibration'
    author = 'PyMoDAQ μRASHG Team'
    version = '1.0.0'
    
    def __init__(self, dashboard):
        """
        Initialize the Elliptec calibration extension.
        
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
        """Start the Elliptec calibration experiment."""
        try:
            # Create the experiment instance
            self.experiment = ElliptecCalibrationExperiment(dashboard=self.dashboard)
            
            # Initialize and show the experiment GUI
            main_widget = self.experiment.ensure_gui_initialized()
            main_widget.show()
            
            logger.info("Started Elliptec calibration experiment")
            
        except Exception as e:
            logger.error(f"Failed to start Elliptec calibration experiment: {e}")
            raise
    
    def stop_extension(self):
        """Stop the Elliptec calibration experiment."""
        try:
            if self.experiment:
                self.experiment.cleanup()
                self.experiment = None
            
            logger.info("Stopped Elliptec calibration experiment")
            
        except Exception as e:
            logger.error(f"Failed to stop Elliptec calibration experiment: {e}")
    
    def get_widget(self):
        """Get the main widget for the experiment."""
        if self.experiment:
            return self.experiment.main_widget
        return None


# Export for PyMoDAQ discovery
__all__ = ['URASHG_Elliptec_Calibration']