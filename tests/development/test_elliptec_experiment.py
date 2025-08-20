#!/usr/bin/env python3
"""
Test script for launching the Elliptec Calibration Experiment
"""

import logging
import sys

from qtpy import QtWidgets

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Launch the Elliptec calibration experiment for testing"""

    # Create QApplication
    app = QtWidgets.QApplication(sys.argv)

    try:
        # Import the experiment
        from src.pymodaq_plugins_urashg.experiments.elliptec_calibration import (
            ElliptecCalibrationExperiment,
        )

        print("✅ Successfully imported ElliptecCalibrationExperiment")

        # Create experiment instance
        experiment = ElliptecCalibrationExperiment()

        print(f"✅ Successfully created experiment: {experiment.experiment_name}")
        print(f"Required modules: {experiment.required_modules}")
        print(f"Optional modules: {experiment.optional_modules}")

        # Show the experiment GUI
        experiment.main_widget.show()
        experiment.main_widget.setWindowTitle("μRASHG Elliptec Calibration Experiment")

        print("✅ Experiment GUI launched successfully!")
        print("The experiment interface is now running.")
        print("Required hardware modules:", experiment.required_modules)
        print("You can now:")
        print("1. Initialize hardware (if available)")
        print("2. Configure experiment parameters")
        print("3. Start calibration procedures")
        print("\nClose the GUI window to exit.")

        # Run the application
        sys.exit(app.exec_())

    except Exception as e:
        print(f"❌ Failed to launch experiment: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    main()
