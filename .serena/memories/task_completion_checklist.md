# Task Completion Checklist

When completing any coding task, always run these commands in order:

## 1. Code Formatting (Required)
```bash
black src/
isort src/
```

## 2. Linting (Required)
```bash
flake8 src/
```

## 3. Testing (Required)
```bash
# Run appropriate tests based on changes made
pytest                    # All tests
pytest tests/unit/        # Unit tests only
pytest tests/mock/        # Mock device tests
pytest -m "not slow"     # Skip slow tests for quick validation
```

## 4. Coverage Check (Optional but Recommended)
```bash
pytest --cov=pymodaq_plugins_urashg --cov-report=term-missing
```

## 5. Pre-commit Validation (If hooks are installed)
```bash
pre-commit run --all-files
```

## Critical Notes
- **Always format before committing**: Black and isort must be run
- **Fix linting errors**: flake8 issues must be resolved
- **Verify tests pass**: At minimum run relevant test categories
- **Hardware tests**: Only run if hardware is available and connected
- **Mock tests**: Always run these as they validate plugin interfaces

## Hardware-Specific Testing
- Only run hardware tests (`pytest tests/integration/ -m "hardware"`) if:
  - Physical hardware is connected and configured
  - You're specifically testing hardware integration
- Mock tests provide adequate coverage for most development scenarios