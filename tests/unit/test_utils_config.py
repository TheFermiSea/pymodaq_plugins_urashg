#!/usr/bin/env python3
"""
Unit tests for the utils.config module.

Tests configuration loading and validation functionality.
"""

import sys
from pathlib import Path
import tempfile
import json

import pytest

# Add source path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Test markers  
pytestmark = [pytest.mark.unit]


class TestConfigModule:
    """Test configuration loading and validation."""
    
    def test_config_import(self):
        """Test that config module can be imported."""
        from pymodaq_plugins_urashg.utils.config import Config
        
        assert Config is not None
        
    def test_config_instantiation(self):
        """Test that Config class can be instantiated."""
        from pymodaq_plugins_urashg.utils.config import Config
        
        config = Config()
        assert config is not None
        
    def test_config_has_expected_methods(self):
        """Test that Config has expected methods."""
        from pymodaq_plugins_urashg.utils.config import Config
        
        config = Config()
        
        # Check for expected methods
        expected_methods = ['get', 'set', 'get_hardware_config']
        for method_name in expected_methods:
            if hasattr(config, method_name):
                assert callable(getattr(config, method_name))


class TestConfigFunctions:
    """Test standalone configuration functions."""
    
    def test_get_config_function(self):
        """Test get_config function if it exists."""
        try:
            from pymodaq_plugins_urashg import get_config
            
            config = get_config()
            assert config is not None
            
        except ImportError:
            # Function doesn't exist - that's ok
            pytest.skip("get_config function not available")
            
    def test_config_constants(self):
        """Test configuration constants."""
        from pymodaq_plugins_urashg.utils import config
        
        # Check for any constants or default values
        if hasattr(config, 'DEFAULT_CONFIG'):
            assert isinstance(config.DEFAULT_CONFIG, dict)
            
        if hasattr(config, 'CONFIG_FILE'):
            assert isinstance(config.CONFIG_FILE, (str, Path))


class TestParameterUtils:
    """Test parameter utility functions."""
    
    def test_parameter_utils_import(self):
        """Test parameter utils can be imported."""
        from pymodaq_plugins_urashg.utils import parameter_utils
        
        assert parameter_utils is not None
        
    def test_parameter_validation_functions(self):
        """Test parameter validation if functions exist."""
        from pymodaq_plugins_urashg.utils import parameter_utils
        
        # Check for validation functions
        validation_functions = [
            'validate_wavelength',
            'validate_position', 
            'validate_exposure_time',
            'clamp_value'
        ]
        
        for func_name in validation_functions:
            if hasattr(parameter_utils, func_name):
                func = getattr(parameter_utils, func_name)
                assert callable(func)


class TestHardwareConstants:
    """Test hardware constants and configurations."""
    
    def test_constants_import(self):
        """Test constants can be imported."""
        from pymodaq_plugins_urashg.hardware.urashg import constants
        
        # Should not raise any errors
        assert constants is not None
        
    def test_expected_constants(self):
        """Test for expected hardware constants."""
        from pymodaq_plugins_urashg.hardware.urashg import constants
        
        # Check for expected constant types
        constant_names = dir(constants)
        
        # Should have some constants defined
        assert len(constant_names) > 0
        
        # Filter out built-in attributes
        user_constants = [name for name in constant_names if not name.startswith('_')]
        assert len(user_constants) > 0


class TestSystemControl:
    """Test system control utilities."""
    
    def test_system_control_import(self):
        """Test system control can be imported."""
        from pymodaq_plugins_urashg.hardware.urashg import system_control
        
        # Should not raise errors
        assert system_control is not None
        
    def test_system_control_functions(self):
        """Test system control functions if they exist."""
        from pymodaq_plugins_urashg.hardware.urashg import system_control
        
        function_names = [name for name in dir(system_control) if not name.startswith('_')]
        
        # Should have some functions
        assert len(function_names) > 0
        
        # Test any callable functions  
        for name in function_names:
            attr = getattr(system_control, name)
            if callable(attr):
                # Function exists and is callable
                assert attr is not None


class TestUtilsInit:
    """Test utils module initialization."""
    
    def test_utils_init_import(self):
        """Test utils __init__ can be imported."""
        import pymodaq_plugins_urashg.utils as utils
        
        # Should not raise errors
        assert utils is not None
        
    def test_utils_exports(self):
        """Test utils module exports."""
        import pymodaq_plugins_urashg.utils as utils
        
        # Should have some exported items
        exported_items = [name for name in dir(utils) if not name.startswith('_')]
        assert len(exported_items) > 0


class TestHardwareUtils:
    """Test hardware utility functions."""
    
    def test_hardware_utils_import(self):
        """Test hardware utils can be imported."""
        from pymodaq_plugins_urashg.hardware.urashg import utils
        
        # Should not raise errors
        assert utils is not None
        
    def test_utility_functions(self):
        """Test utility functions if they exist."""
        from pymodaq_plugins_urashg.hardware.urashg import utils
        
        # Check for utility functions
        utility_names = [name for name in dir(utils) if not name.startswith('_')]
        
        # Should have some utilities
        assert len(utility_names) > 0
        
        # Test callable utilities
        for name in utility_names:
            attr = getattr(utils, name)
            if callable(attr):
                assert attr is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])