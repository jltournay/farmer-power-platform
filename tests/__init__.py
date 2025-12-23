"""
Farmer Power Platform Test Suite

This package contains all tests for the Farmer Power Platform.

Test Structure:
    tests/
    ├── unit/                  # Fast, isolated unit tests
    │   ├── collection/        # Collection Model tests
    │   ├── plantation/        # Plantation Model tests
    │   ├── knowledge/         # Knowledge Model tests
    │   ├── action_plan/       # Action Plan Model tests
    │   ├── notification/      # Notification Model tests
    │   ├── market_analysis/   # Market Analysis Model tests
    │   ├── ai_model/          # AI Model tests
    │   └── conversational_ai/ # Conversational AI Model tests
    ├── integration/           # Integration tests (cross-model)
    ├── golden/                # Golden sample accuracy tests
    ├── contracts/             # Contract/schema validation tests
    └── fixtures/              # Test data and mocks

Running Tests:
    pytest tests/                    # All tests
    pytest tests/unit/               # Unit tests only
    pytest tests/golden/ -m golden   # Golden sample tests
    pytest tests/ -m "not slow"      # Skip slow tests
    pytest tests/ --cov=src          # With coverage

References:
    - Test Design: _bmad-output/test-design-system-level.md
    - Project Context: _bmad-output/project-context.md
"""
