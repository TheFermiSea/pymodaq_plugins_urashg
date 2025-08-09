# PyMoDAQ Plugin Threading Safety Guidelines

## Overview

This document outlines threading safety best practices for PyMoDAQ plugin development, based on issues discovered and resolved in the URASHG plugin package.

## ⚠️ Critical Issue: `__del__` Methods and QThread Crashes

### The Problem

PyMoDAQ plugins run within Qt's threading system. When hardware controller classes implement `__del__` methods that call cleanup functions like `disconnect()`, they can cause "QThread: Destroyed while thread is still running" crashes during garbage collection.

### Root Cause

```python
# ❌ PROBLEMATIC PATTERN
class HardwareController:
    def __del__(self):
        """Cleanup on destruction."""
        try:
            self.disconnect()  # This can interfere with Qt threading!
        except Exception:
            pass
```

**Why this fails:**
1. `__del__` is called during garbage collection
2. Garbage collection can happen at any time, including during Qt thread cleanup
3. `disconnect()` often involves serial communication, thread synchronization, or resource cleanup
4. This creates a race condition with Qt's thread destruction process

### ✅ Solution: Explicit Cleanup

Remove `__del__` methods from hardware controllers and rely on explicit cleanup through the PyMoDAQ plugin lifecycle:

```python
# ✅ SAFE PATTERN
class HardwareController:
    # Note: __del__ method removed to prevent QThread destruction conflicts
    # Cleanup is handled explicitly via disconnect() in the plugin's close() method
    pass

class DAQ_Plugin(DAQ_Move_base):
    def close(self):
        """Explicit cleanup called by PyMoDAQ framework."""
        try:
            if self.controller:
                self.controller.disconnect()  # Safe explicit cleanup
                self.controller = None
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
```

## 🔧 Fixed Controllers

The following controllers in the URASHG package have been fixed:

### ESP300Controller
- **File**: `src/pymodaq_plugins_urashg/hardware/urashg/esp300_controller.py`
- **Issue**: `__del__` method calling `self.disconnect()`
- **Fix**: Removed `__del__` method, cleanup handled in `DAQ_Move_ESP300.close()`
- **Status**: ✅ Verified working

### Newport1830C_controller  
- **File**: `src/pymodaq_plugins_urashg/hardware/urashg/newport1830c_controller.py`
- **Issue**: `__del__` method calling `self.disconnect()`
- **Fix**: Removed `__del__` method, cleanup handled in `DAQ_0DViewer_Newport1830C.close()`
- **Status**: ✅ Fixed

## 🧪 Testing Threading Safety

### Test Script
A comprehensive test script is available: `test_hardware_controller_threading.py`

```bash
python test_hardware_controller_threading.py
```

### Test Results
```
ESP300 Controller: ✅ PASSED
Stress Test (10 cycles): ✅ PASSED  
Garbage Collection: ✅ PASSED
```

## 📋 Best Practices Checklist

### ✅ Hardware Controller Classes

- [ ] **No `__del__` methods** that call cleanup functions
- [ ] **Explicit disconnect methods** for resource cleanup
- [ ] **Thread-safe operations** using locks where necessary
- [ ] **Graceful error handling** in cleanup methods
- [ ] **Proper resource management** (close serial ports, release hardware)

### ✅ PyMoDAQ Plugin Classes

- [ ] **Implement `close()` method** for explicit cleanup
- [ ] **Call controller disconnect** in plugin's `close()` method
- [ ] **Set controller to None** after cleanup
- [ ] **Handle cleanup errors gracefully** without crashing
- [ ] **Test with mock mode** for development without hardware

### ✅ Development Workflow

- [ ] **Test plugin initialization** in mock mode
- [ ] **Test multiple init/close cycles** (stress testing)
- [ ] **Verify garbage collection** doesn't cause crashes
- [ ] **Test with real hardware** when available
- [ ] **Check PyMoDAQ dashboard integration** 

## 🔍 Identifying Potential Issues

### Search for Problematic Patterns

```bash
# Find __del__ methods in hardware controllers
grep -r "def __del__" src/*/hardware/

# Find disconnect calls in __del__ methods
grep -A 5 -B 2 "__del__" src/ | grep -A 5 disconnect
```

### Warning Signs

1. **"QThread: Destroyed while thread is still running"** errors
2. **"IOT instruction (core dumped)"** crashes
3. **Dashboard crashes during plugin initialization**
4. **Inconsistent plugin cleanup behavior**
5. **Memory leaks or resource not released**

## 🛠️ Migration Guide

### For Existing Hardware Controllers

1. **Identify** controllers with `__del__` methods:
   ```python
   def __del__(self):
       try:
           self.disconnect()  # ❌ Remove this pattern
       except:
           pass
   ```

2. **Remove** the `__del__` method entirely:
   ```python
   # Note: __del__ method removed to prevent QThread destruction conflicts
   # Cleanup is handled explicitly via disconnect() in the plugin's close() method
   ```

3. **Ensure** the PyMoDAQ plugin calls cleanup explicitly:
   ```python
   def close(self):
       if self.controller:
           self.controller.disconnect()
           self.controller = None
   ```

4. **Test** the changes with the provided test scripts

### For New Controllers

- **Never implement `__del__` methods** that perform I/O or cleanup
- **Design for explicit cleanup** from the start
- **Use context managers** (`with` statements) for resource management when possible
- **Follow the established patterns** in fixed controllers

## 🚀 Benefits of Explicit Cleanup

1. **Predictable cleanup timing** - No reliance on garbage collection
2. **Better error handling** - Cleanup errors can be properly logged
3. **Thread safety** - No interference with Qt's threading system
4. **Resource management** - Guaranteed cleanup when plugin closes
5. **Debugging** - Clear cleanup sequence in logs

## 📖 References

- [PyMoDAQ Plugin Development Guide](https://pymodaq.cnrs.fr/en/latest/)
- [Qt Threading Best Practices](https://doc.qt.io/qt-5/thread-basics.html)
- [Python `__del__` Method Gotchas](https://docs.python.org/3/reference/datamodel.html#object.__del__)

## 🤝 Contributing

When adding new hardware controllers:

1. **Follow these guidelines** from the start
2. **Add threading safety tests** for new controllers  
3. **Update this document** with new patterns or issues found
4. **Review existing code** for similar issues

---

**Last Updated**: August 2025  
**Status**: Active maintenance  
**Contact**: PyMoDAQ Plugin Development Team