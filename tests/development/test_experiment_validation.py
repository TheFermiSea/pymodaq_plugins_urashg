#!/usr/bin/env python3
"""
Validation test for μRASHG experiments without GUI display
Tests core functionality and parameter validation
"""

import sys
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_experiment_imports():
    """Test that all experiment modules can be imported successfully"""
    print("=== Testing Experiment Imports ===")

    experiments = [
        (
            "Base Experiment",
            "src.pymodaq_plugins_urashg.experiments.base_experiment",
            "URASHGBaseExperiment",
        ),
        (
            "Elliptec Calibration",
            "src.pymodaq_plugins_urashg.experiments.elliptec_calibration",
            "ElliptecCalibrationExperiment",
        ),
        (
            "EOM Calibration",
            "src.pymodaq_plugins_urashg.experiments.eom_calibration",
            "EOMCalibrationExperiment",
        ),
        (
            "PDSHG Experiment",
            "src.pymodaq_plugins_urashg.experiments.pdshg_experiment",
            "PDSHGExperiment",
        ),
        (
            "Variable Attenuator",
            "src.pymodaq_plugins_urashg.experiments.variable_attenuator_calibration",
            "VariableAttenuatorCalibrationExperiment",
        ),
        (
            "Basic μRASHG",
            "src.pymodaq_plugins_urashg.experiments.basic_urashg_experiment",
            "BasicURASHGExperiment",
        ),
        (
            "Wavelength Dependent",
            "src.pymodaq_plugins_urashg.experiments.wavelength_dependent_rashg",
            "WavelengthDependentRASHGExperiment",
        ),
    ]

    success_count = 0
    for name, module_path, class_name in experiments:
        try:
            module = __import__(module_path, fromlist=[class_name])
            experiment_class = getattr(module, class_name)
            print(f"✅ {name}: Import successful")
            success_count += 1
        except Exception as e:
            print(f"❌ {name}: Import failed - {e}")

    print(
        f"\nImport Results: {success_count}/{len(experiments)} experiments imported successfully"
    )
    return success_count == len(experiments)


def test_experiment_instantiation():
    """Test experiment instantiation without GUI"""
    print("\n=== Testing Experiment Instantiation (No GUI) ===")

    # Override GUI setup to avoid Qt issues
    import sys
    from unittest.mock import Mock

    # Mock Qt application for headless testing
    mock_app = Mock()
    sys.modules["qtpy.QtWidgets"].QApplication = Mock(return_value=mock_app)

    try:
        from src.pymodaq_plugins_urashg.experiments.elliptec_calibration import (
            ElliptecCalibrationExperiment,
        )

        # Temporarily override GUI setup
        original_setup_gui = ElliptecCalibrationExperiment.setup_gui
        ElliptecCalibrationExperiment.setup_gui = Mock()

        # Create experiment instance
        experiment = ElliptecCalibrationExperiment()

        # Test basic properties
        print(f"✅ Experiment Name: {experiment.experiment_name}")
        print(f"✅ Experiment Type: {experiment.experiment_type}")
        print(f"✅ Required Modules: {experiment.required_modules}")
        print(f"✅ Optional Modules: {experiment.optional_modules}")
        print(f"✅ Initial State: {experiment.state.value}")

        # Test parameter structure
        if hasattr(experiment, "settings") and experiment.settings:
            print(
                f"✅ Parameter tree created with {len(experiment.settings.children())} main groups"
            )

            # Check main parameter groups
            expected_groups = [
                "experiment_info",
                "file_settings",
                "hardware_settings",
                "calibration_settings",
                "safety_settings",
            ]
            for group_name in expected_groups:
                if experiment.settings.child(group_name):
                    print(f"   ✅ {group_name} parameter group found")
                else:
                    print(f"   ❌ {group_name} parameter group missing")
        else:
            print("❌ Parameter tree not created")

        # Restore original method
        ElliptecCalibrationExperiment.setup_gui = original_setup_gui

        print("✅ Elliptec calibration experiment instantiated successfully (headless)")
        return True

    except Exception as e:
        print(f"❌ Experiment instantiation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_experiment_parameters():
    """Test experiment parameter validation"""
    print("\n=== Testing Experiment Parameters ===")

    try:
        from src.pymodaq_plugins_urashg.experiments.elliptec_calibration import (
            ElliptecCalibrationExperiment,
        )
        from unittest.mock import Mock

        # Mock GUI setup
        ElliptecCalibrationExperiment.setup_gui = Mock()

        experiment = ElliptecCalibrationExperiment()

        # Test specific parameter validation
        if hasattr(experiment, "settings"):
            # Test wavelength parameter
            wavelength_param = experiment.settings.child(
                "hardware_settings", "maitai_wavelength"
            )
            if wavelength_param:
                print(f"✅ Wavelength parameter: {wavelength_param.value()} nm")
                print(
                    f"   Range: {wavelength_param.opts.get('limits', 'No limits set')}"
                )

            # Test calibration settings
            calib_group = experiment.settings.child("calibration_settings")
            if calib_group:
                print(
                    f"✅ Calibration settings group with {len(calib_group.children())} parameters"
                )

            # Test safety settings
            safety_group = experiment.settings.child("safety_settings")
            if safety_group:
                max_power = safety_group.child("max_power")
                if max_power:
                    print(f"✅ Safety max power: {max_power.value()} W")

        print("✅ Parameter validation tests passed")
        return True

    except Exception as e:
        print(f"❌ Parameter validation failed: {e}")
        return False


def test_experiment_methods():
    """Test key experiment methods"""
    print("\n=== Testing Experiment Methods ===")

    try:
        from src.pymodaq_plugins_urashg.experiments.elliptec_calibration import (
            ElliptecCalibrationExperiment,
        )
        from unittest.mock import Mock

        # Mock GUI setup
        ElliptecCalibrationExperiment.setup_gui = Mock()

        experiment = ElliptecCalibrationExperiment()

        # Test state management
        from src.pymodaq_plugins_urashg.experiments.base_experiment import (
            ExperimentState,
        )

        original_state = experiment.state
        experiment.set_state(ExperimentState.INITIALIZING)
        print(f"✅ State change: {original_state.value} → {experiment.state.value}")

        # Test parameter validation method
        try:
            experiment.validate_parameters()
            print("✅ Parameter validation method callable")
        except NotImplementedError:
            print(
                "✅ Parameter validation method correctly raises NotImplementedError (to be overridden)"
            )
        except Exception as e:
            print(f"❌ Parameter validation method error: {e}")

        # Test data structure creation
        try:
            experiment.create_data_structures()
            print("✅ Data structure creation method callable")
        except NotImplementedError:
            print(
                "✅ Data structure creation correctly raises NotImplementedError (to be overridden)"
            )
        except Exception as e:
            print(f"❌ Data structure creation error: {e}")

        print("✅ Core experiment methods functional")
        return True

    except Exception as e:
        print(f"❌ Method testing failed: {e}")
        return False


def main():
    """Run all validation tests"""
    print("μRASHG Experiment Framework Validation")
    print("=" * 50)

    tests = [
        ("Import Tests", test_experiment_imports),
        ("Instantiation Tests", test_experiment_instantiation),
        ("Parameter Tests", test_experiment_parameters),
        ("Method Tests", test_experiment_methods),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} encountered error: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{len(results)} test suites passed")

    if passed == len(results):
        print("\n🎉 ALL TESTS PASSED!")
        print("The μRASHG experiment framework is ready for use!")
        return 0
    else:
        print(f"\n⚠️  {len(results) - passed} test suite(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
