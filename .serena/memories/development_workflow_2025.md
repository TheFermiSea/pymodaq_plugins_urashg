# Development Workflow and Tools Used (2025)

## AI Collaboration Protocol
- **Claude**: Primary commander for tool calling, decision-making, and workflow orchestration
- **Gemini**: Deep analysis specialist for comprehensive codebase/documentation review (when available)
- **Serena**: Memory management and symbol-level code operations
- **Container-use**: Isolated testing environments for parallel development

## Container Environments Used
- `related-fly`: Code quality fixes and linting (Python 3.11-slim base)
- `helping-cicada`: Unit test execution and validation (Python 3.11-slim base)
- Both environments configured with pytest, black, isort, flake8

## Code Quality Standards Applied
- **Black**: Line length 88 characters, automatic formatting
- **Isort**: Import sorting with PySide6 in known_third_party
- **Flake8**: Linting with E203,W503 ignored (black compatibility)
- **Pytest**: Unit testing with hardware/mock markers

## Git Workflow Notes
- Work done in container environments requires committing changes to include in git
- Use `container-use checkout <env_id>` to access environment-specific changes
- Remember to sync changes back to main repository before final commits

## Testing Strategy
- Unit tests run in isolated containers without hardware dependencies
- Mock device patterns implemented for hardware abstraction
- Entry point validation confirms PyMoDAQ plugin discovery
- All 8 tests pass in PyMoDAQ 5.0+ environment