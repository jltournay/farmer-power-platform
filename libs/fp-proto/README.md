# fp-proto

Generated Protocol Buffer stubs for Farmer Power Platform.

## Overview

This library contains auto-generated Python code from `.proto` definitions. **DO NOT EDIT MANUALLY** - regenerate using the generation script.

## Generation

To regenerate the stubs from proto definitions:

```bash
./scripts/proto-gen.sh
```

## Requirements

For generation only:
- `grpcio-tools >= 1.60.0`
- `mypy-protobuf >= 3.5.0` (optional, for type stubs)

For runtime:
- `grpcio >= 1.60.0`
- `protobuf >= 4.25.0`

## Usage

```python
from fp_proto.plantation.v1 import (
    PlantationServiceStub,
    GetFarmerRequest,
    Farmer,
    Region,
    Factory,
)
```

## Structure

```
libs/fp-proto/
├── src/fp_proto/
│   ├── __init__.py
│   └── plantation/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── plantation_pb2.py      # Message definitions
│           ├── plantation_pb2.pyi     # Type stubs
│           └── plantation_pb2_grpc.py # Service stubs
└── pyproject.toml
```

## Proto Sources

Proto definitions are located in `proto/` at the repository root:

- `proto/plantation/v1/plantation.proto` - Plantation Model service definitions
