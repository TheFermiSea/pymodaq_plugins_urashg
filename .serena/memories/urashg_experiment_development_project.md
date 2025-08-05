# uRASHG Experiment Development Project Plan

## Project Objective
Develop a comprehensive suite of PyMoDAQ experiments for micro Rotational Anisotropy Second Harmonic Generation (μRASHG) microscopy system.

## Multi-Agent Development Fleet

### Agent 1: Repository Research Agent
- **Role**: Analyze existing urashg_2 repository and extract experimental principles
- **Tasks**: 
  - Clone and analyze git@github.com:TheFermiSea/urashg_2.git
  - Work with Gemini to understand experimental workflows
  - Document calibration procedures, experiment types, and data structures
  - Create comprehensive development plan based on existing knowledge

### Agent 2: PyMoDAQ Experiment Developer
- **Role**: Implement PyMoDAQ-compliant experiments one by one
- **Tasks**:
  - Develop calibration experiments (EOM, Elliptec rotators)
  - Implement power-dependent RASHG experiments
  - Create wavelength-dependent RASHG experiments  
  - Design time-resolved RASHG using ESP300
  - Follow PyMoDAQ standards and conventions

### Agent 3: Code Review Agent
- **Role**: Ensure code quality and PyMoDAQ best practices
- **Tasks**:
  - Review all experimental code for logical soundness
  - Verify adherence to PyMoDAQ conventions
  - Test integration with existing plugin infrastructure
  - Suggest improvements and optimizations

## Shared Resources
- **Serena Memory System**: All agents share context, findings, and decisions
- **Version Control**: Incremental commits on "experiments" branch
- **Tool Usage**: All agents use available tools (LSP, file operations, testing)

## Target Experiments
1. EOM calibration and characterization
2. Elliptec rotator calibration 
3. Power-dependent RASHG measurements
4. Wavelength-dependent RASHG scans
5. Time-resolved RASHG with ESP300 motion control
6. Custom experiment framework for user-defined protocols

## Development Branch
Working on: `experiments` branch
Base: Current main branch with verified hardware functionality