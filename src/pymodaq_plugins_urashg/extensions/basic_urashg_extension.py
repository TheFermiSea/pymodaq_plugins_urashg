# -*- coding: utf-8 -*-
"""
Basic μRASHG Experiment Extension for PyMoDAQ

This extension provides a PyMoDAQ-compliant wrapper for the basic μRASHG experiment.
It allows the experiment to be discovered and launched from the PyMoDAQ dashboard.
"""

import logging
from pathlib import Path

from pymodaq_gui.utils.custom_app import CustomApp

from ..experiments.basic_urashg_experiment import BasicURASHGExperiment

logger = logging.getLogger(__name__)


class URASHG_Basic_Experiment(CustomApp):
    """
    PyMoDAQ extension for basic μRASHG experiment.
    
    This extension provides complete 4D μRASHG measurements with
    camera detection and multi-dimensional data collection.
    """
    
    # Extension metadata
    name = 'Basic μRASHG Experiment'
    description = 'Complete μRASHG measurements with camera'
    author = 'PyMoDAQ μRASHG Team'
    version = '1.0.0'
    
    def __init__(self, dashboard):
        """
        Initialize the basic μRASHG experiment extension.
        
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
        """Start the basic μRASHG experiment."""
        try:
            # Create the experiment instance
            self.experiment = BasicURASHGExperiment(dashboard=self.dashboard)
            
            # Initialize and show the experiment GUI
            main_widget = self.experiment.ensure_gui_initialized()
            main_widget.show()
            
            logger.info("Started basic μRASHG experiment")
            
        except Exception as e:
            logger.error(f"Failed to start basic μRASHG experiment: {e}")
            raise
    
    def stop_extension(self):
        """Stop the basic μRASHG experiment."""
        try:
            if self.experiment:
                self.experiment.cleanup()
                self.experiment = None
            
            logger.info("Stopped basic μRASHG experiment")
            
        except Exception as e:
            logger.error(f"Failed to stop basic μRASHG experiment: {e}")
    
    def get_widget(self):
        """Get the main widget for the experiment."""
        if self.experiment:
            return self.experiment.main_widget
        return None


# Export for PyMoDAQ discovery
__all__ = ['URASHG_Basic_Experiment']