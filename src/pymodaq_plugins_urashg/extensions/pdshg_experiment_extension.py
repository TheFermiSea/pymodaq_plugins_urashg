# -*- coding: utf-8 -*-
"""
μRASHG PDSHG Experiment Extension for PyMoDAQ

This extension provides a PyMoDAQ-compliant wrapper for the Power-Dependent RASHG experiment.
It allows the experiment to be discovered and launched from the PyMoDAQ dashboard.
"""

import logging
from pathlib import Path

from pymodaq_gui.utils.custom_app import CustomApp

from ..experiments.pdshg_experiment import PDSHGExperiment

logger = logging.getLogger(__name__)


class URASHG_PDSHG_Experiment(CustomApp):
    """
    PyMoDAQ extension for μRASHG Power-Dependent RASHG experiment.
    
    This extension provides power-dependent RASHG measurements with
    real-time curve fitting and cos²(2θ + φ) angular dependence analysis.
    """
    
    # Extension metadata
    name = 'μRASHG PDSHG Experiment'
    description = 'Power-dependent RASHG measurements with fitting'
    author = 'PyMoDAQ μRASHG Team'
    version = '1.0.0'
    
    def __init__(self, dashboard):
        """
        Initialize the PDSHG experiment extension.
        
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
        """Start the PDSHG experiment."""
        try:
            # Create the experiment instance
            self.experiment = PDSHGExperiment(dashboard=self.dashboard)
            
            # Initialize and show the experiment GUI
            main_widget = self.experiment.ensure_gui_initialized()
            main_widget.show()
            
            logger.info("Started PDSHG experiment")
            
        except Exception as e:
            logger.error(f"Failed to start PDSHG experiment: {e}")
            raise
    
    def stop_extension(self):
        """Stop the PDSHG experiment."""
        try:
            if self.experiment:
                self.experiment.cleanup()
                self.experiment = None
            
            logger.info("Stopped PDSHG experiment")
            
        except Exception as e:
            logger.error(f"Failed to stop PDSHG experiment: {e}")
    
    def get_widget(self):
        """Get the main widget for the experiment."""
        if self.experiment:
            return self.experiment.main_widget
        return None


# Export for PyMoDAQ discovery
__all__ = ['URASHG_PDSHG_Experiment']