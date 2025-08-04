# -*- coding: utf-8 -*-
"""
Parameter utility functions for PyMoDAQ 5.x compatibility.
"""

def child_exists(param, *path):
    """
    Check if a child parameter exists at the given path.
    
    Args:
        param: Parent parameter
        *path: Path components to child parameter
        
    Returns:
        bool: True if child exists, False otherwise
    """
    try:
        param.child(*path)
        return True
    except:
        return False

def get_child_value(param, *path, default=None):
    """
    Get child parameter value with default fallback.
    
    Args:
        param: Parent parameter
        *path: Path components to child parameter
        default: Default value if child doesn't exist
        
    Returns:
        Value of child parameter or default
    """
    try:
        return param.child(*path).value()
    except:
        return default

def set_child_value(param, *path_and_value):
    """
    Set child parameter value safely.
    
    Args:
        param: Parent parameter
        *path_and_value: Path components followed by value
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        *path, value = path_and_value
        param.child(*path).setValue(value)
        return True
    except:
        return False