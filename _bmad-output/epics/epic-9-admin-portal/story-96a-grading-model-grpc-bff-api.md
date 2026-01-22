# Story 9.6a: Grading Model gRPC + BFF API

As a **Platform Administrator**,
I want the backend API to support listing and retrieving grading models,
So that the Admin UI can display grading models and their assignments.

> **Context:** Story 9.6 was split because the original assumed `ListGradingModels` gRPC existed - it doesn't. This story adds the missing backend infrastructure.

## Background

### What Exists
- Proto: `CreateGradingModel`, `GetGradingModel`, `GetFactoryGradingModel`, `AssignGradingModelToFactory`
- Plantation Service: All 4 methods implemented
- fp-common: `GradingModel` Pydantic model exists
- Repository: `GradingModelRepository` in Plantation Model

### What's Missing
- Proto: `ListGradingModels` RPC (paginated list endpoint)
- fp-common: Proto converters for GradingModel
- BFF: Plantation client methods, schemas, transformer, REST routes

## Acceptance Criteria

**AC 9.6a.1: Proto ListGradingModels RPC**

**Given** the plantation.proto file
**When** I add the ListGradingModels RPC
**Then** it includes:
  - `ListGradingModelsRequest` with optional filters (crop_type, market, status) and pagination
  - `ListGradingModelsResponse` with repeated GradingModel and pagination token
  - Standard pagination pattern matching other List* RPCs

**AC 9.6a.2: Plantation Service Implementation**

**Given** the ListGradingModels RPC is defined
**When** I implement the handler in PlantationService
**Then** it:
  - Queries GradingModelRepository with filters
  - Supports pagination (page_size, page_token)
  - Returns models with factory_count (number of factories using each model)

**AC 9.6a.3: fp-common Converters**

**Given** the GradingModel Pydantic model exists
**When** I add converters to `plantation_converters.py`
**Then** I have:
  - `grading_model_from_proto(proto) -> GradingModel`
  - `grading_model_to_proto(model) -> plantation_pb2.GradingModel`

**AC 9.6a.4: BFF Plantation Client Methods**

**Given** the gRPC service is implemented
**When** I add methods to PlantationClient
**Then** I have:
  - `list_grading_models(filters, page_size, page_token) -> GradingModelListResponse`
  - `get_grading_model(model_id) -> GradingModel`
  - `assign_grading_model_to_factory(model_id, factory_id) -> GradingModel`

**AC 9.6a.5: BFF REST API Endpoints**

**Given** the BFF client methods exist
**When** I create `routes/admin/grading_models.py`
**Then** I have:
  - `GET /api/admin/grading-models` - List with filters and pagination
  - `GET /api/admin/grading-models/{model_id}` - Get single model with details
  - `POST /api/admin/grading-models/{model_id}/assign` - Assign to factory

**AC 9.6a.6: BFF Schemas and Transformer**

**Given** the REST endpoints exist
**When** I create schemas and transformer
**Then** I have:
  - `GradingModelResponse` - Single model with all fields
  - `GradingModelListResponse` - Paginated list
  - `AssignGradingModelRequest` - factory_id
  - `grading_model_transformer.py` - Proto to JSON transformation

## Technical Notes

### Proto Addition (plantation.proto)
```protobuf
rpc ListGradingModels(ListGradingModelsRequest) returns (ListGradingModelsResponse);

message ListGradingModelsRequest {
  string crop_type = 1;      // Optional filter
  string market = 2;         // Optional filter
  string status = 3;         // Optional: active, draft, archived
  int32 page_size = 10;
  string page_token = 11;
}

message ListGradingModelsResponse {
  repeated GradingModel grading_models = 1;
  string next_page_token = 2;
  int32 total_count = 3;
}
```

### BFF Route Registration
Add to `bff/api/routes/admin/__init__.py`:
```python
from .grading_models import router as grading_models_router
admin_router.include_router(grading_models_router, prefix="/grading-models", tags=["Admin - Grading Models"])
```

### Patterns to Follow
- ADR-012: BFF patterns (client → service → transformer → route)
- ADR-004: fp-common converters
- Existing admin routes: `factories.py`, `regions.py` as reference

## Dependencies
- Story 1.6: Grading Model Configuration (provides GradingModel proto message) - DONE
- Story 9.1c: Admin Portal BFF Endpoints (provides admin route patterns) - DONE

## Blocks
- Story 9.6b: Grading Model Management UI

## Story Points: 5

## Out of Scope
- UI implementation (Story 9.6b)
- Grading model CRUD (managed by farmer-power-training)
- Grading model versioning logic
