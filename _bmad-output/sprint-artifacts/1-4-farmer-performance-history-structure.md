# Story 1.4: Farmer Performance History Structure

**Status:** ready-for-dev

---

## Story

As a **factory quality manager**,
I want farmer performance metrics tracked over time with attribute-level detail,
So that I can identify trends, understand root causes, and target improvement efforts.

---

## Acceptance Criteria

1. **Given** a grading model configuration exists (e.g., TBK Kenya Tea)
   **When** I store it in the Plantation Model via gRPC
   **Then** the grading model is persisted with: model_id, version, grading_type, attributes (with classes), grade_rules, grade_labels, active_at_factory[]

2. **Given** a factory has an assigned grading model
   **When** I query get_factory_grading_model(factory_id)
   **Then** the response includes the complete grading model definition (attributes, classes, rules, labels)

3. **Given** a farmer exists in the system
   **When** the farmer_performance subdocument is initialized
   **Then** it contains: grading_model_id, grading_model_version, empty historical metrics (grade_distribution, attribute_distributions), empty today metrics

4. **Given** a farmer has performance data
   **When** I query get_farmer_summary(farmer_id)
   **Then** the response includes: grading_model reference, historical grade distributions, historical attribute distributions, today metrics, trend direction

---

## Tasks / Subtasks

- [ ] **Task 1: Define GradingModel Pydantic models** (AC: #1, #2)
  - [ ] 1.1 Create `domain/models/grading_model.py` with GradingModel model
  - [ ] 1.2 Define GradingAttribute model (num_classes, classes list)
  - [ ] 1.3 Define GradeRules model (reject_conditions, conditional_reject)
  - [ ] 1.4 Define GradingType enum (BINARY, TERNARY, MULTI_LEVEL)
  - [ ] 1.5 Add factory methods for validation and serialization

- [ ] **Task 2: Define FarmerPerformance Pydantic models** (AC: #3, #4)
  - [ ] 2.1 Create `domain/models/farmer_performance.py` with FarmerPerformance model
  - [ ] 2.2 Define HistoricalMetrics with grade_distribution and attribute_distributions per period (30d/90d/year)
  - [ ] 2.3 Define TodayMetrics with grade counts, attribute counts, and grading_model reference
  - [ ] 2.4 Define TrendDirection enum (IMPROVING, STABLE, DECLINING)
  - [ ] 2.5 Add factory methods for default/empty performance initialization

- [ ] **Task 3: Update Proto definitions** (AC: #1, #2, #3, #4)
  - [ ] 3.1 Add `GradingModel` message to plantation.proto
  - [ ] 3.2 Add `GradingAttribute` message with classes repeated field
  - [ ] 3.3 Add `GradeRules` message with reject_conditions and conditional_reject
  - [ ] 3.4 Add `GradingType` enum (GRADING_TYPE_BINARY, GRADING_TYPE_TERNARY, GRADING_TYPE_MULTI_LEVEL)
  - [ ] 3.5 Add `FarmerPerformance` message with attribute_distributions
  - [ ] 3.6 Add `HistoricalMetrics` message with grade_distribution and attribute_distributions maps
  - [ ] 3.7 Add `TrendDirection` enum
  - [ ] 3.8 Add `CreateGradingModelRequest/Response` messages
  - [ ] 3.9 Add `GetFactoryGradingModelRequest/Response` messages
  - [ ] 3.10 Add `GetFarmerSummaryRequest` and `FarmerSummary` response message
  - [ ] 3.11 Add RPCs: CreateGradingModel, GetGradingModel, GetFactoryGradingModel, GetFarmerSummary
  - [ ] 3.12 Regenerate Python stubs via `./scripts/proto-gen.sh`

- [ ] **Task 4: Implement GradingModelRepository** (AC: #1, #2)
  - [ ] 4.1 Create `infrastructure/repositories/grading_model_repository.py`
  - [ ] 4.2 Implement `create()` - store new grading model
  - [ ] 4.3 Implement `get_by_id()` - fetch grading model by model_id + version
  - [ ] 4.4 Implement `get_active_for_factory()` - fetch grading model assigned to factory
  - [ ] 4.5 Implement `update()` - update grading model (new version)
  - [ ] 4.6 Implement `list_all()` - list all grading models
  - [ ] 4.7 Add indexes on model_id, active_at_factory

- [ ] **Task 5: Implement FarmerPerformanceRepository** (AC: #3, #4)
  - [ ] 5.1 Create `infrastructure/repositories/farmer_performance_repository.py`
  - [ ] 5.2 Implement `get_by_farmer_id()` - fetch performance for a farmer
  - [ ] 5.3 Implement `upsert()` - create or update performance data
  - [ ] 5.4 Implement `initialize_for_farmer()` - create default performance on farmer registration
  - [ ] 5.5 Add indexes on farmer_id, updated_at

- [ ] **Task 6: Implement gRPC methods** (AC: #1, #2, #4)
  - [ ] 6.1 Add CreateGradingModel to PlantationServiceServicer
  - [ ] 6.2 Add GetGradingModel to PlantationServiceServicer
  - [ ] 6.3 Add GetFactoryGradingModel to PlantationServiceServicer
  - [ ] 6.4 Add GetFarmerSummary to PlantationServiceServicer
  - [ ] 6.5 Return combined farmer profile + performance data in GetFarmerSummary
  - [ ] 6.6 Handle NOT_FOUND when farmer/grading_model doesn't exist
  - [ ] 6.7 Return default performance metrics if no performance data yet

- [ ] **Task 7: Auto-initialize performance on farmer registration** (AC: #3)
  - [ ] 7.1 Hook into farmer creation in PlantationServiceServicer.CreateFarmer
  - [ ] 7.2 Lookup factory's grading model to get grading_model_id
  - [ ] 7.3 Call FarmerPerformanceRepository.initialize_for_farmer() after farmer creation
  - [ ] 7.4 Initialize with empty/default values for all metrics, referencing the grading model

- [ ] **Task 8: Write unit tests** (AC: #1, #2, #3, #4)
  - [ ] 8.1 Test GradingModel model validation (attributes, rules, labels)
  - [ ] 8.2 Test FarmerPerformance model validation
  - [ ] 8.3 Test GradingModelRepository CRUD operations
  - [ ] 8.4 Test FarmerPerformanceRepository CRUD operations
  - [ ] 8.5 Test CreateGradingModel gRPC method
  - [ ] 8.6 Test GetFactoryGradingModel gRPC method
  - [ ] 8.7 Test GetFarmerSummary gRPC method
  - [ ] 8.8 Test auto-initialization on farmer registration

- [ ] **Task 9: Integration tests**
  - [ ] 9.1 Test grading model creation and retrieval flow
  - [ ] 9.2 Test farmer registration creates performance record with correct grading_model_id
  - [ ] 9.3 Test GetFarmerSummary returns complete performance data

---

## Dev Notes

### Service Location

All code goes in the existing Plantation Model service:

```
services/plantation-model/
├── src/plantation_model/
│   ├── domain/
│   │   ├── models/
│   │   │   ├── grading_model.py          # NEW - Grading model definition
│   │   │   ├── farmer_performance.py     # NEW - Performance domain model
│   │   │   └── ...
│   ├── infrastructure/
│   │   └── repositories/
│   │       ├── grading_model_repository.py      # NEW
│   │       ├── farmer_performance_repository.py # NEW
│   │       └── ...
│   └── api/
│       └── plantation_service.py         # EXTEND - add gRPC methods
└── ...
```

### GradingModel Schema

**Source:** [_bmad-output/analysis/tbk-kenya-tea-grading-model-specification.md]

```yaml
# MongoDB: grading_models (owned by Plantation Model)
grading_model:
  # Identity
  model_id: "tbk_kenya_tea_v1"
  model_version: "1.0.0"
  regulatory_authority: "Tea Board of Kenya (TBK)"
  crops_name: "Tea"
  market_name: "Kenya_TBK"
  grading_type: "binary"  # binary | ternary | multi_level

  # Attribute structure (defines what the CV model outputs)
  attributes:
    leaf_type:
      num_classes: 7
      classes: ["bud", "one_leaf_bud", "two_leaves_bud", "three_plus_leaves_bud", "single_soft_leaf", "coarse_leaf", "banji"]
    coarse_subtype:
      num_classes: 4
      classes: ["none", "double_luck", "maintenance_leaf", "hard_leaf"]
    banji_hardness:
      num_classes: 2
      classes: ["soft", "hard"]

  # Grade calculation rules
  grade_rules:
    reject_conditions:
      leaf_type: ["three_plus_leaves_bud", "coarse_leaf"]
    conditional_reject:
      - if_attribute: "leaf_type"
        if_value: "banji"
        then_attribute: "banji_hardness"
        reject_values: ["hard"]

  # Display labels (internal → display)
  grade_labels:
    ACCEPT: "Primary"
    REJECT: "Secondary"

  # Deployment
  active_at_factory: ["factory-001", "factory-002"]

  # Timestamps
  created_at: datetime
  updated_at: datetime
```

### GradingModel Pydantic Models

```python
# domain/models/grading_model.py
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GradingType(str, Enum):
    """Type of grading system."""
    BINARY = "binary"           # Accept/Reject, Primary/Secondary
    TERNARY = "ternary"         # Premium/Standard/Reject
    MULTI_LEVEL = "multi_level" # A/B/C/D or custom levels


class GradingAttribute(BaseModel):
    """Definition of a single attribute in the grading model."""
    num_classes: int = Field(ge=2, description="Number of classes for this attribute")
    classes: list[str] = Field(min_length=2, description="Class labels in order")


class ConditionalReject(BaseModel):
    """Conditional rejection rule."""
    if_attribute: str
    if_value: str
    then_attribute: str
    reject_values: list[str]


class GradeRules(BaseModel):
    """Rules for determining final grade from attributes."""
    reject_conditions: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Attribute values that always result in rejection"
    )
    conditional_reject: list[ConditionalReject] = Field(
        default_factory=list,
        description="Conditional rejection rules"
    )


class GradingModel(BaseModel):
    """Complete grading model definition stored in Plantation Model."""

    # Identity
    model_id: str = Field(description="Unique identifier for this grading model")
    model_version: str = Field(description="Semantic version (e.g., 1.0.0)")
    regulatory_authority: Optional[str] = Field(
        default=None,
        description="Regulatory body that defines this grading standard"
    )
    crops_name: str = Field(description="Crop type (e.g., Tea, Coffee)")
    market_name: str = Field(description="Market identifier (e.g., Kenya_TBK)")
    grading_type: GradingType = Field(description="Type of grading system")

    # Attribute structure
    attributes: dict[str, GradingAttribute] = Field(
        description="Attribute definitions keyed by attribute name"
    )

    # Grade calculation rules
    grade_rules: GradeRules = Field(default_factory=GradeRules)

    # Display labels
    grade_labels: dict[str, str] = Field(
        description="Internal grade → display label mapping"
    )

    # Deployment
    active_at_factory: list[str] = Field(
        default_factory=list,
        description="Factory IDs where this model is active"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def get_all_attribute_classes(self) -> dict[str, list[str]]:
        """Return all classes for all attributes."""
        return {name: attr.classes for name, attr in self.attributes.items()}

    def get_grade_display_label(self, internal_grade: str) -> str:
        """Convert internal grade to display label."""
        return self.grade_labels.get(internal_grade, internal_grade)

    model_config = {
        "json_schema_extra": {
            "example": {
                "model_id": "tbk_kenya_tea_v1",
                "model_version": "1.0.0",
                "regulatory_authority": "Tea Board of Kenya (TBK)",
                "crops_name": "Tea",
                "market_name": "Kenya_TBK",
                "grading_type": "binary",
                "attributes": {
                    "leaf_type": {
                        "num_classes": 7,
                        "classes": ["bud", "one_leaf_bud", "two_leaves_bud",
                                   "three_plus_leaves_bud", "single_soft_leaf",
                                   "coarse_leaf", "banji"]
                    }
                },
                "grade_labels": {"ACCEPT": "Primary", "REJECT": "Secondary"},
                "active_at_factory": ["factory-001"]
            }
        }
    }
```

### FarmerPerformance Schema (Updated with Attribute Tracking)

```yaml
# MongoDB: farmer_performance
farmer_performance:
  farmer_id: string

  # Grading model reference (for interpreting distributions)
  grading_model_id: string
  grading_model_version: string

  # Farm context (denormalized for efficient computation)
  farm_size_hectares: number
  farm_scale: enum  # "smallholder" | "medium" | "estate"

  # Historical (updated by batch job - Epic 5/6)
  historical:
    # Grade-level distributions
    grade_distribution_30d: object   # {"Primary": 120, "Secondary": 30}
    grade_distribution_90d: object
    grade_distribution_year: object

    # Attribute-level distributions (enables root-cause analysis)
    attribute_distributions_30d: object
    # Example: {
    #   "leaf_type": {"bud": 15, "one_leaf_bud": 45, ...},
    #   "coarse_subtype": {"double_luck": 3, ...},
    #   "banji_hardness": {"soft": 3, "hard": 2}
    # }
    attribute_distributions_90d: object
    attribute_distributions_year: object

    # Derived metrics (computed from distributions)
    primary_percentage_30d: number   # Convenience: derived from grade_distribution
    primary_percentage_90d: number
    primary_percentage_year: number

    # Yield metrics
    total_kg_30d: number
    total_kg_90d: number
    total_kg_year: number
    yield_kg_per_hectare_30d: number
    yield_kg_per_hectare_90d: number
    yield_kg_per_hectare_year: number

    # Trend and timing
    improvement_trend: enum  # "improving" | "stable" | "declining"
    computed_at: datetime

  # Today (updated by streaming events - later story when Collection Model exists)
  today:
    deliveries: number
    total_kg: number
    grade_counts: object           # {"Primary": 5, "Secondary": 2}
    attribute_counts: object       # Same structure as attribute_distributions
    last_delivery: datetime
    date: date                     # Resets when date changes
```

### FarmerPerformance Pydantic Models

```python
# domain/models/farmer_performance.py
from datetime import datetime, date, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from plantation_model.domain.models.farmer import FarmScale


class TrendDirection(str, Enum):
    """Trend direction for farmer performance."""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


class HistoricalMetrics(BaseModel):
    """Historical performance metrics computed by batch job."""

    # Grade-level distributions
    grade_distribution_30d: dict[str, int] = Field(default_factory=dict)
    grade_distribution_90d: dict[str, int] = Field(default_factory=dict)
    grade_distribution_year: dict[str, int] = Field(default_factory=dict)

    # Attribute-level distributions (enables root-cause analysis)
    # Structure: {"attribute_name": {"class_name": count, ...}, ...}
    attribute_distributions_30d: dict[str, dict[str, int]] = Field(default_factory=dict)
    attribute_distributions_90d: dict[str, dict[str, int]] = Field(default_factory=dict)
    attribute_distributions_year: dict[str, dict[str, int]] = Field(default_factory=dict)

    # Derived convenience metrics
    primary_percentage_30d: float = Field(default=0.0, ge=0.0, le=100.0)
    primary_percentage_90d: float = Field(default=0.0, ge=0.0, le=100.0)
    primary_percentage_year: float = Field(default=0.0, ge=0.0, le=100.0)

    # Volume metrics
    total_kg_30d: float = Field(default=0.0, ge=0.0)
    total_kg_90d: float = Field(default=0.0, ge=0.0)
    total_kg_year: float = Field(default=0.0, ge=0.0)

    # Yield metrics
    yield_kg_per_hectare_30d: float = Field(default=0.0, ge=0.0)
    yield_kg_per_hectare_90d: float = Field(default=0.0, ge=0.0)
    yield_kg_per_hectare_year: float = Field(default=0.0, ge=0.0)

    # Trend
    improvement_trend: TrendDirection = Field(default=TrendDirection.STABLE)
    computed_at: Optional[datetime] = None


class TodayMetrics(BaseModel):
    """Today's performance metrics (updated by streaming events)."""

    deliveries: int = Field(default=0, ge=0)
    total_kg: float = Field(default=0.0, ge=0.0)

    # Grade-level counts for today
    grade_counts: dict[str, int] = Field(default_factory=dict)

    # Attribute-level counts for today
    # Structure: {"attribute_name": {"class_name": count, ...}, ...}
    attribute_counts: dict[str, dict[str, int]] = Field(default_factory=dict)

    last_delivery: Optional[datetime] = None
    date: date = Field(default_factory=lambda: date.today())


class FarmerPerformance(BaseModel):
    """Complete farmer performance tracking with attribute-level detail."""

    farmer_id: str = Field(description="Reference to farmer")

    # Grading model reference (for interpreting distributions)
    grading_model_id: str = Field(description="Reference to grading model")
    grading_model_version: str = Field(description="Grading model version")

    # Farm context (denormalized)
    farm_size_hectares: float = Field(ge=0.01, le=1000.0)
    farm_scale: FarmScale

    # Performance metrics
    historical: HistoricalMetrics = Field(default_factory=HistoricalMetrics)
    today: TodayMetrics = Field(default_factory=TodayMetrics)

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @classmethod
    def initialize_for_farmer(
        cls,
        farmer_id: str,
        farm_size_hectares: float,
        farm_scale: FarmScale,
        grading_model_id: str,
        grading_model_version: str,
    ) -> "FarmerPerformance":
        """Create default performance record for a new farmer."""
        return cls(
            farmer_id=farmer_id,
            grading_model_id=grading_model_id,
            grading_model_version=grading_model_version,
            farm_size_hectares=farm_size_hectares,
            farm_scale=farm_scale,
        )

    def get_attribute_trend(
        self,
        attribute_name: str,
        class_name: str
    ) -> Optional[str]:
        """
        Compare 30d vs 90d distribution for a specific attribute class.
        Returns: "increasing", "decreasing", "stable", or None if insufficient data.
        """
        dist_30d = self.historical.attribute_distributions_30d.get(attribute_name, {})
        dist_90d = self.historical.attribute_distributions_90d.get(attribute_name, {})

        count_30d = dist_30d.get(class_name, 0)
        count_90d = dist_90d.get(class_name, 0)

        # Need data in both periods
        total_30d = sum(dist_30d.values()) if dist_30d else 0
        total_90d = sum(dist_90d.values()) if dist_90d else 0

        if total_30d < 3 or total_90d < 3:
            return None

        pct_30d = count_30d / total_30d
        pct_90d = count_90d / total_90d

        if pct_30d > pct_90d * 1.1:  # 10% threshold
            return "increasing"
        elif pct_30d < pct_90d * 0.9:
            return "decreasing"
        else:
            return "stable"

    model_config = {
        "json_schema_extra": {
            "example": {
                "farmer_id": "WM-0001",
                "grading_model_id": "tbk_kenya_tea_v1",
                "grading_model_version": "1.0.0",
                "farm_size_hectares": 1.5,
                "farm_scale": "medium",
                "historical": {
                    "grade_distribution_30d": {"Primary": 120, "Secondary": 30},
                    "attribute_distributions_30d": {
                        "leaf_type": {
                            "bud": 15,
                            "one_leaf_bud": 45,
                            "two_leaves_bud": 50,
                            "three_plus_leaves_bud": 10,
                            "coarse_leaf": 15,
                            "banji": 5
                        },
                        "banji_hardness": {"soft": 3, "hard": 2}
                    },
                    "primary_percentage_30d": 80.0,
                    "improvement_trend": "improving"
                },
                "today": {
                    "deliveries": 2,
                    "total_kg": 45.0,
                    "grade_counts": {"Primary": 2},
                    "attribute_counts": {
                        "leaf_type": {"two_leaves_bud": 2}
                    }
                }
            }
        }
    }
```

### Proto Updates Required

Update `proto/plantation/v1/plantation.proto`:

```protobuf
// ============================================================
// Grading Model Messages
// ============================================================

enum GradingType {
  GRADING_TYPE_UNSPECIFIED = 0;
  GRADING_TYPE_BINARY = 1;
  GRADING_TYPE_TERNARY = 2;
  GRADING_TYPE_MULTI_LEVEL = 3;
}

message GradingAttribute {
  int32 num_classes = 1;
  repeated string classes = 2;
}

message ConditionalReject {
  string if_attribute = 1;
  string if_value = 2;
  string then_attribute = 3;
  repeated string reject_values = 4;
}

message GradeRules {
  map<string, RejectCondition> reject_conditions = 1;
  repeated ConditionalReject conditional_reject = 2;
}

message RejectCondition {
  repeated string values = 1;
}

message GradingModel {
  string model_id = 1;
  string model_version = 2;
  string regulatory_authority = 3;
  string crops_name = 4;
  string market_name = 5;
  GradingType grading_type = 6;
  map<string, GradingAttribute> attributes = 7;
  GradeRules grade_rules = 8;
  map<string, string> grade_labels = 9;
  repeated string active_at_factory = 10;
  google.protobuf.Timestamp created_at = 11;
  google.protobuf.Timestamp updated_at = 12;
}

// ============================================================
// Farmer Performance Messages
// ============================================================

enum TrendDirection {
  TREND_UNSPECIFIED = 0;
  TREND_IMPROVING = 1;
  TREND_STABLE = 2;
  TREND_DECLINING = 3;
}

// Nested map for attribute distributions: attribute_name -> class_name -> count
message AttributeClassCounts {
  map<string, int32> class_counts = 1;
}

message HistoricalMetrics {
  // Grade distributions
  map<string, int32> grade_distribution_30d = 1;
  map<string, int32> grade_distribution_90d = 2;
  map<string, int32> grade_distribution_year = 3;

  // Attribute distributions
  map<string, AttributeClassCounts> attribute_distributions_30d = 4;
  map<string, AttributeClassCounts> attribute_distributions_90d = 5;
  map<string, AttributeClassCounts> attribute_distributions_year = 6;

  // Derived metrics
  double primary_percentage_30d = 7;
  double primary_percentage_90d = 8;
  double primary_percentage_year = 9;

  // Volume
  double total_kg_30d = 10;
  double total_kg_90d = 11;
  double total_kg_year = 12;

  // Yield
  double yield_kg_per_hectare_30d = 13;
  double yield_kg_per_hectare_90d = 14;
  double yield_kg_per_hectare_year = 15;

  // Trend
  TrendDirection improvement_trend = 16;
  google.protobuf.Timestamp computed_at = 17;
}

message TodayMetrics {
  int32 deliveries = 1;
  double total_kg = 2;
  map<string, int32> grade_counts = 3;
  map<string, AttributeClassCounts> attribute_counts = 4;
  google.protobuf.Timestamp last_delivery = 5;
  string date = 6;  // YYYY-MM-DD format
}

message FarmerPerformance {
  string farmer_id = 1;
  string grading_model_id = 2;
  string grading_model_version = 3;
  double farm_size_hectares = 4;
  FarmScale farm_scale = 5;
  HistoricalMetrics historical = 6;
  TodayMetrics today = 7;
  google.protobuf.Timestamp created_at = 8;
  google.protobuf.Timestamp updated_at = 9;
}

// ============================================================
// Request/Response Messages
// ============================================================

message CreateGradingModelRequest {
  GradingModel grading_model = 1;
}

message CreateGradingModelResponse {
  GradingModel grading_model = 1;
}

message GetGradingModelRequest {
  string model_id = 1;
  string model_version = 2;  // Optional: if empty, returns latest
}

message GetGradingModelResponse {
  GradingModel grading_model = 1;
}

message GetFactoryGradingModelRequest {
  string factory_id = 1;
}

message GetFactoryGradingModelResponse {
  GradingModel grading_model = 1;
}

message GetFarmerSummaryRequest {
  string farmer_id = 1;
}

message FarmerSummary {
  Farmer farmer = 1;
  FarmerPerformance performance = 2;
  GradingModel grading_model = 3;  // Include for display label lookup
}

// ============================================================
// Service Definition
// ============================================================

service PlantationService {
  // ... existing RPCs ...

  // Grading Model RPCs
  rpc CreateGradingModel(CreateGradingModelRequest) returns (CreateGradingModelResponse);
  rpc GetGradingModel(GetGradingModelRequest) returns (GetGradingModelResponse);
  rpc GetFactoryGradingModel(GetFactoryGradingModelRequest) returns (GetFactoryGradingModelResponse);

  // Farmer Summary RPC
  rpc GetFarmerSummary(GetFarmerSummaryRequest) returns (FarmerSummary);
}
```

### MongoDB Indexes

```javascript
// Collection: grading_models
db.grading_models.createIndex({ "model_id": 1, "model_version": 1 }, { unique: true });
db.grading_models.createIndex({ "active_at_factory": 1 });
db.grading_models.createIndex({ "market_name": 1 });

// Collection: farmer_performance
db.farmer_performance.createIndex({ "farmer_id": 1 }, { unique: true });
db.farmer_performance.createIndex({ "grading_model_id": 1 });
db.farmer_performance.createIndex({ "updated_at": 1 });
```

### Testing Strategy

**Unit Tests (`tests/unit/plantation/`):**
- `test_grading_model.py` - GradingModel validation, rules, labels
- `test_farmer_performance_model.py` - FarmerPerformance validation, attribute tracking
- `test_grading_model_repository.py` - Repository CRUD operations
- `test_farmer_performance_repository.py` - Repository CRUD operations
- `test_grpc_grading_model.py` - CreateGradingModel, GetFactoryGradingModel
- `test_grpc_farmer_summary.py` - GetFarmerSummary gRPC method

**Integration Tests (`tests/integration/`):**
- `test_grading_model_flow.py` - End-to-end grading model creation and retrieval
- `test_farmer_registration_creates_performance.py` - Auto-init with grading model reference

### Critical Implementation Rules

**From project-context.md:**

1. **ALL I/O operations MUST be async** - Repository methods
2. **Use Pydantic 2.0 syntax** - `model_dump()`, `model_config` attribute
3. **Type hints required** - ALL function signatures
4. **Absolute imports only** - No relative imports
5. **NEVER hardcode grade labels** - Use grading model for lookup

### What This Story Does NOT Include

| Excluded | Reason | Future Story |
|----------|--------|--------------|
| Event subscription | Collection Model doesn't exist yet | Epic 2 |
| Performance aggregation logic | Batch job responsibility | Epic 5/6 |
| Trend calculation | Requires historical data from batch job | Epic 5/6 |
| Yield percentile calculation | Requires cross-farmer aggregation | Epic 5/6 |
| Regional benchmark comparison | Requires batch job | Epic 5/6 |

**This story focuses on:**
- Data structure definitions (GradingModel, FarmerPerformance)
- Storage (repositories for both entities)
- Basic gRPC CRUD operations
- Auto-initialization on farmer registration

### References

- [Source: _bmad-output/analysis/tbk-kenya-tea-grading-model-specification.md] - TBK grading model spec
- [Source: _bmad-output/architecture/plantation-model-architecture.md] - Plantation Model architecture
- [Source: _bmad-output/project-context.md] - Critical rules
- [Source: proto/plantation/v1/plantation.proto] - Existing proto definitions
- [Source: services/plantation-model/src/plantation_model/domain/models/farmer.py] - Farmer model patterns

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List