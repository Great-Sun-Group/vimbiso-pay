#!/bin/bash

# Update ValidationResult imports
find app/core -type f -name "*.py" -exec sed -i 's/from core\.utils\.error_types import ValidationResult/from core.error.types import ValidationResult/g' {} +

# Update ErrorContext imports
find app/core -type f -name "*.py" -exec sed -i 's/from core\.utils\.error_types import ErrorContext/from core.error.types import ErrorContext/g' {} +
