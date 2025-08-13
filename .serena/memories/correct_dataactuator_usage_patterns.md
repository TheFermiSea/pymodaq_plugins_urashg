# Correct DataActuator Usage Patterns for PyMoDAQ 5.x

## Critical Pattern: Single-axis vs Multi-axis Controllers

### ✅ Single-Axis Controllers (MaiTai, simple motors)
```python
def move_abs(self, position: Union[float, DataActuator]):
    if isinstance(position, DataActuator):
        target_value = float(position.value())  # CORRECT!
    else:
        target_value = float(position)
```

### ✅ Multi-Axis Controllers (Elliptec, ESP300, XYZ stages)
```python
def move_abs(self, positions: Union[List[float], DataActuator]):
    if isinstance(positions, DataActuator):
        # Multi-axis: positions.data[0] is numpy array with multiple values
        target_positions_array = positions.data[0]  # CORRECT!
        target_positions_list = target_positions_array.tolist()
    else:
        target_positions_list = positions
```

## ❌ Common Mistakes to Avoid

### Wrong Single-Axis Pattern
```python
# NEVER do this for single-axis controllers:
if isinstance(position, DataActuator):
    target_value = float(position.data[0][0])  # WRONG! Causes UI integration failure
```

### Wrong Multi-Axis Pattern
```python
# NEVER do this for multi-axis controllers:
if isinstance(positions, DataActuator):
    target_values = float(positions.value())  # WRONG! Multi-axis needs array access
```

## Official PyMoDAQ Examples Reference
- **Arduino LED Plugin**: Uses `position.value()` for single-axis
- **Physik Instrumente Plugin**: Uses `position.value()` for single-axis  
- **SmarAct MCS2 Plugin**: Uses `position.data[0]` for multi-axis arrays

## Testing Validation
- Import test: Plugin should import without errors
- UI Integration: DataActuator values should be properly extracted from PyMoDAQ interface
- Hardware Communication: Controller should receive correct numerical values

## Key Rule
**Use `.value()` for single values, use `.data[0]` for arrays**