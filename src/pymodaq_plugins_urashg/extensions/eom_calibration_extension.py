# -*- coding: utf-8 -*-
"""
μRASHG EOM Calibration Extension for PyMoDAQ

This extension provides a PyMoDAQ-compliant wrapper for the EOM calibration experiment.
It allows the experiment to be discovered and launched from the PyMoDAQ dashboard.
"""

import logging
from pathlib import Path

from pymodaq_gui.utils.custom_app import CustomApp

from ..experiments.eom_calibration import EOMCalibrationExperiment

logger = logging.getLogger(__name__)


class URASHG_EOM_Calibration(CustomApp):
    """
    PyMoDAQ extension for μRASHG EOM calibration experiment.
    
    This extension provides PID-based laser power control calibration
    with real-time feedback and validation capabilities.
    """
    
    # Extension metadata
    name = 'μRASHG EOM Calibration'
    description = 'EOM power control calibration with PID feedback'
    author = 'PyMoDAQ μRASHG Team'
    version = '1.0.0'
    
    def __init__(self, dashboard):
        """
        Initialize the EOM calibration extension.
        
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
        """Start the EOM calibration experiment."""
        try:
            # Create the experiment instance
            self.experiment = EOMCalibrationExperiment(dashboard=self.dashboard)
            
            # Initialize and show the experiment GUI
            main_widget = self.experiment.ensure_gui_initialized()
            main_widget.show()
            
            logger.info("Started EOM calibration experiment")
            
        except Exception as e:
            logger.error(f"Failed to start EOM calibration experiment: {e}")
            raise
    
    def stop_extension(self):
        """Stop the EOM calibration experiment."""
        try:
            if self.experiment:
                self.experiment.cleanup()
                self.experiment = None
            
            logger.info("Stopped EOM calibration experiment")
            
        except Exception as e:
            logger.error(f"Failed to stop EOM calibration experiment: {e}")
    
    def get_widget(self):
        """Get the main widget for the experiment."""
        if self.experiment:
            return self.experiment.main_widget
        return None


# Export for PyMoDAQ discovery
__all__ = ['URASHG_EOM_Calibration']