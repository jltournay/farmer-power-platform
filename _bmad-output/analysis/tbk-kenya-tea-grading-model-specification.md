# TBK Kenya Tea Grading Model Specification

**Version:** 1.1
**Date:** 2025-12-22
**Status:** Draft
**Author:** Business Analyst (Mary)
**Regulatory Authority:** Tea Board of Kenya (TBK)

> **Dependency:** This specification requires [farmer-power-qc-analyzer#3](https://github.com/farmerpower-ai/farmer-power-qc-analyzer/issues/3) to be implemented for conditional reject logic support.
>
> **Implementation:** [farmer-power-training#20](https://github.com/farmerpower-ai/farmer-power-training/issues/20) - TBK grading model training and configuration.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Regulatory Context](#regulatory-context)
3. [Grading Model Design](#grading-model-design)
4. [MarketGradingConfig (Python)](#marketgradingconfig-python)
5. [ONNX Model Metadata](#onnx-model-metadata)
6. [Labeling Guide](#labeling-guide)
7. [Training Requirements](#training-requirements)
8. [Integration with Farmer Power Platform](#integration-with-farmer-power-platform)
9. [Appendices](#appendices)

---

## Executive Summary

This specification defines the grading model configuration for tea quality assessment in Kenya, based on the official criteria established by the **Tea Board of Kenya (TBK)** under the Tea Act 2020.

The TBK grading system is a **binary classification** (Primary/Secondary) based on leaf type assessment. This document provides the complete technical specification required to:

1. Train the vision model in `farmer-power-training`
2. Configure the Farmer Power QC Analyzer
3. Integrate grading results with the Farmer Power Platform

---

## Regulatory Context

### Authority

- **Regulatory Body:** Tea Board of Kenya (TBK)
- **Legal Framework:** Tea Act 2020
- **Website:** https://www.teaboard.or.ke/
- **Scope:** Production, promotion, standards, and trade of tea in Kenya

### Official Grade Definitions

| Grade | Quality Level | Description |
|-------|---------------|-------------|
| **Primary** | Best Quality | Tea leaves meeting premium plucking standards |
| **Secondary** | Lower Quality | Tea leaves not meeting primary standards |

### TBK Leaf Classification Criteria

| Leaf Type | Grade | Rationale |
|-----------|-------|-----------|
| Bud | Primary | Unopened leaf tip, highest quality |
| One leaf and a bud | Primary | Fine plucking standard |
| Two leaves and a bud | Primary | Standard fine plucking |
| Three leaves and a bud (or more) | Secondary | Coarse plucking |
| Single soft leaf | Primary | Tender young leaf |
| Coarse leaf (incl. double luck, maintenance leaf, hard leaf) | Secondary | Mature, fibrous leaves |
| Soft Banji | Primary | Dormant but pliable shoot |
| Hard Banji | Secondary | Dormant and rigid shoot |

---

## Grading Model Design

### Architecture: Multi-Head Classification

The model uses a **3-head architecture** to capture the hierarchical nature of TBK classification:

```
                    ┌─────────────────────────────┐
                    │       Input Image           │
                    │     (Tea Leaf Sample)       │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │   Shared Feature Backbone   │
                    │  (EfficientNet/MobileNet)   │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
     ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
     │     HEAD 1      │  │     HEAD 2      │  │     HEAD 3      │
     │   leaf_type     │  │ coarse_subtype  │  │ banji_hardness  │
     │   (7 classes)   │  │  (4 classes)    │  │  (2 classes)    │
     └─────────────────┘  └─────────────────┘  └─────────────────┘
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │      Grading Logic          │
                    │   Primary / Secondary       │
                    └─────────────────────────────┘
```

### Attribute Definitions

#### Head 1: `leaf_type` (Primary Classification)

| Class | Description | Direct Grade |
|-------|-------------|--------------|
| `bud` | Unopened leaf tip, tightly furled | Primary |
| `one_leaf_bud` | One open leaf + visible bud | Primary |
| `two_leaves_bud` | Two open leaves + visible bud | Primary |
| `three_plus_leaves_bud` | Three or more leaves + bud | Secondary |
| `single_soft_leaf` | Single tender/flexible leaf | Primary |
| `coarse_leaf` | Thick, rigid, mature leaf | Secondary (→ Head 2) |
| `banji` | Dormant/stunted shoot | Conditional (→ Head 3) |

#### Head 2: `coarse_subtype` (Coarse Leaf Detail)

*Only evaluated when `leaf_type == coarse_leaf`*

| Class | Description | Grade |
|-------|-------------|-------|
| `none` | Not applicable (leaf_type ≠ coarse_leaf) | N/A |
| `double_luck` | Two fused/joined leaves | Secondary |
| `maintenance_leaf` | Pruning regrowth, irregular shape | Secondary |
| `hard_leaf` | Thick veins, leathery texture | Secondary |

#### Head 3: `banji_hardness` (Banji Determination)

*Only evaluated when `leaf_type == banji`*

| Class | Description | Grade |
|-------|-------------|-------|
| `soft` | Pliable, lighter green, smooth | Primary |
| `hard` | Rigid, darker, fibrous structure | Secondary |

### Grade Calculation Logic

The grade calculation logic is the responsibility of the farmer_power_qc_analyzer project, and it is not part of this project. The model classifies each leave in a bag. There is no grading for the bag as a whole, like the sorting zone in the QC Analyzer routes each leaf in the corresponding grading storing bin.  



---

## MarketGradingConfig (JSON)

This configuration should be placed in the `farmer-power-training` repository at:
`training/grading/configs`


````json
{
    "crops_name": "tea",
    "market_name": "Kenya",
    "grading_model_id": "tbk_kenya_tea_v1",
    "grading_model_version": "1.0.0",
    "grading_type": "binary",
    "attributes": {
      "leaf_type": {
        "num_classes": 7,
        "classes": [
          "bud",
          "one_leaf_bud",
          "two_leaves_bud",
          "three_plus_leaves_bud",
          "single_soft_leaf",
          "coarse_leaf",
          "banji"
        ]
      },
      "coarse_subtype": {
        "num_classes": 4,
        "classes": [
          "none",
          "double_luck",
          "maintenance_leaf",
          "hard_leaf"
        ]
      },
      "banji_hardness": {
        "num_classes": 2,
        "classes": [
          "soft",
          "hard"
        ]
      }
    },
    "grade_rules": {
      "binary_labels": {
        "ACCEPT": "primary",
        "REJECT": "secondary"
      },
      "reject_conditions": {
        "leaf_type": [
          "three_plus_leaves_bud",
          "coarse_leaf"
        ]
      },
      "conditional_reject": [
        {
          "if_attribute": "leaf_type",
          "if_value": "banji",
          "then_attribute": "banji_hardness",
          "reject_values": [
            "hard"
          ]
        }
      ]
    },
    "attribute_weights": {
      "leaf_type": 1.0,
      "coarse_subtype": 0.0,
      "banji_hardness": 0.0
    },
    "grade_thresholds": {},
    "perfect_grade": "primary",
    "attributes_list": [
      "leaf_type",
      "coarse_subtype",
      "banji_hardness"
    ]
}

````


## Labeling Guide

### For Annotators: TBK Kenya Tea Leaf Classification

#### General Instructions

1. Each image shows a single tea leaf or shoot
2. You must label **all three attributes** for every image
3. Use `none` or `soft` (default) for attributes that don't apply
4. When uncertain, choose the more conservative (lower quality) option

#### Visual Recognition Guide

##### Head 1: Leaf Type

| Class | Visual Indicators | Reference Image |
|-------|-------------------|-----------------|
| `bud` | Tightly furled, unopened, pointed tip, silvery-green | [TBD] |
| `one_leaf_bud` | One small open leaf attached to visible bud | [TBD] |
| `two_leaves_bud` | Two open leaves with bud visible between them | [TBD] |
| `three_plus_leaves_bud` | Three or more leaves, bud may be hidden | [TBD] |
| `single_soft_leaf` | Single detached leaf, tender, flexible when bent | [TBD] |
| `coarse_leaf` | Thick, rigid, dark green, prominent veins | [TBD] |
| `banji` | Stunted shoot, compact, dormant appearance | [TBD] |

##### Head 2: Coarse Subtype

*Only label meaningfully when `leaf_type = coarse_leaf`*

| Class | Visual Indicators |
|-------|-------------------|
| `none` | Use when leaf_type is NOT coarse_leaf |
| `double_luck` | Two leaves fused/joined at base |
| `maintenance_leaf` | Irregular shape from pruning regrowth |
| `hard_leaf` | Leathery texture, very thick veins, dark color |

##### Head 3: Banji Hardness

*Only label meaningfully when `leaf_type = banji`*

| Class | Visual Indicators |
|-------|-------------------|
| `soft` | Pliable appearance, lighter green, smooth surface |
| `hard` | Rigid appearance, darker, visible fibrous structure |

#### Labeling Decision Tree

```
START
  │
  ├─ Is it a bud (unopened, furled)?
  │    YES → leaf_type=bud, coarse_subtype=none, banji_hardness=soft
  │
  ├─ Is it a bud with 1 leaf?
  │    YES → leaf_type=one_leaf_bud, coarse_subtype=none, banji_hardness=soft
  │
  ├─ Is it a bud with 2 leaves?
  │    YES → leaf_type=two_leaves_bud, coarse_subtype=none, banji_hardness=soft
  │
  ├─ Is it a bud with 3+ leaves?
  │    YES → leaf_type=three_plus_leaves_bud, coarse_subtype=none, banji_hardness=soft
  │
  ├─ Is it a single detached soft leaf?
  │    YES → leaf_type=single_soft_leaf, coarse_subtype=none, banji_hardness=soft
  │
  ├─ Is it a thick/rigid/mature leaf?
  │    YES → leaf_type=coarse_leaf
  │           │
  │           ├─ Is it two fused leaves?
  │           │    YES → coarse_subtype=double_luck
  │           ├─ Is it pruning regrowth?
  │           │    YES → coarse_subtype=maintenance_leaf
  │           └─ Is it leathery/very thick?
  │                YES → coarse_subtype=hard_leaf
  │
  │           → banji_hardness=soft (default)
  │
  └─ Is it a dormant/stunted shoot (banji)?
       YES → leaf_type=banji, coarse_subtype=none
              │
              ├─ Is it pliable/soft?
              │    YES → banji_hardness=soft
              └─ Is it rigid/hard?
                   YES → banji_hardness=hard
```

#### Common Mistakes to Avoid

| Mistake | Correct Approach |
|---------|------------------|
| Labeling coarse_subtype for non-coarse leaves | Always use `none` when leaf_type ≠ coarse_leaf |
| Confusing 2-leaf with 3-leaf | Count carefully; if uncertain, count as 3+ |
| Mistaking banji for bud | Banji is stunted/dormant; bud is growing tip |
| Ignoring texture for banji | Hardness is critical - test pliability visually |

---

## Training Requirements

### Dataset Specifications

| Attribute | Minimum Samples/Class | Total Minimum | Recommended |
|-----------|----------------------|---------------|-------------|
| `leaf_type` (7 classes) | 1,000 | 7,000 | 10,000+ |
| `coarse_subtype` (4 classes) | 500 | 2,000 | 3,000+ |
| `banji_hardness` (2 classes) | 500 | 1,000 | 2,000+ |

**Total recommended dataset size:** 12,000 - 15,000 labeled images

### Data Collection Strategy

1. **Source:** Farmer Power QC Analyzer cameras at Kenya pilot sites
2. **Mode:** Detection mode (capture + bounding boxes)
3. **Distribution:** Ensure balanced class representation
4. **Seasons:** Collect across wet and dry seasons for variation
5. **Factories:** Multiple factory locations for diversity

### Training Configuration

```python
# Suggested training hyperparameters
TRAINING_CONFIG = {
    'backbone': 'efficientnet_b0',  # or 'mobilenetv3_small' for speed
    'input_size': (224, 224),
    'batch_size': 32,
    'epochs': 50,
    'learning_rate': 0.001,
    'optimizer': 'AdamW',
    'scheduler': 'CosineAnnealingLR',
    'loss_weights': {
        'leaf_type': 1.0,
        'coarse_subtype': 0.5,  # Lower weight - conditional
        'banji_hardness': 0.5   # Lower weight - conditional
    },
    'augmentation': [
        'RandomHorizontalFlip',
        'RandomRotation(15)',
        'ColorJitter(brightness=0.2, contrast=0.2)',
        'RandomResizedCrop(224, scale=(0.8, 1.0))'
    ]
}
```

### Expected Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| `leaf_type` accuracy | > 92% | Primary classification |
| `coarse_subtype` accuracy | > 88% | Conditional attribute |
| `banji_hardness` accuracy | > 90% | Binary decision |
| Overall grade accuracy | > 95% | Primary/Secondary |
| Inference throughput | > 60 img/sec | On Raspberry Pi 5 |

---

## Integration with Farmer Power Platform

### Grading Result Schema

The QC Analyzer will output grading results in this format for ingestion by the Collection Model:

The QC Analyzer will output a JSON file with the result of the grading process for a tea bag for ingestion by the Collection Model

Example of a quality result for a tea bag with 102 tea leaves. The tea bag is classified with 61 leaves classified as `primary` and 41 leaves classified as `secondary`.

```json
{
  "market_name": "Kenya",
  "crop_name": "tea",
  "grading_model_version": "1.0.0",
  "grading_model_id": "tbk_kenya_tea_v1",
  "timestamp": "2025-12-22T10:30:45Z",
  "bag_id": "2dd2fa43-85be-4fe6-a44a-b209135d9e9f",
  "factory_id": "KEN-FAC-001",
  "farmer_id": "KEN-FRM-567890",
  "total": 102,
  "attribute_distribution": {
    "leaf_type": {
      "two_leaves_bud": {
        "count": 11,
        "avg_confidence": 0.8273
      },
      "banji": {
        "count": 12,
        "avg_confidence": 0.8075
      },
      "one_leaf_bud": {
        "count": 15,
        "avg_confidence": 0.8267
      },
      "single_soft_leaf": {
        "count": 16,
        "avg_confidence": 0.8206
      },
      "three_plus_leaves_bud": {
        "count": 20,
        "avg_confidence": 0.873
      },
      "bud": {
        "count": 12,
        "avg_confidence": 0.9067
      },
      "coarse_leaf": {
        "count": 16,
        "avg_confidence": 0.8469
      }
    },
    "coarse_subtype": {
      "hard_leaf": {
        "count": 25,
        "avg_confidence": 0.8444
      },
      "double_luck": {
        "count": 25,
        "avg_confidence": 0.8304
      },
      "maintenance_leaf": {
        "count": 28,
        "avg_confidence": 0.8582
      },
      "none": {
        "count": 24,
        "avg_confidence": 0.8438
      }
    },
    "banji_hardness": {
      "soft": {
        "count": 55,
        "avg_confidence": 0.8445
      },
      "hard": {
        "count": 47,
        "avg_confidence": 0.8606
      }
    }
  },
  "primary": 61,
  "secondary": 41
}


```


### Plantation Model Linkage

The grading results will be linked to:

- **Farm:** via `farmer_id`
- **Factory:** via `factory_id`
- **Grading Model:** via `grading_model_id`

### Analytics Dimensions

The multi-attribute model enables rich analytics:

| Analysis | Enabled By |
|----------|------------|
| Primary/Secondary trends | `grade` |
| Plucking quality patterns | `leaf_type` distribution |
| Coarse leaf root cause | `coarse_subtype` breakdown |
| Banji management issues | `banji_hardness` ratio |
| Farmer improvement tracking | Historical grade trends |

---

## Appendices

### A. Glossary

| Term | Definition |
|------|------------|
| **Banji** | A dormant or stunted tea shoot that has stopped growing |
| **Double Luck** | Two leaves that have fused together during growth |
| **Maintenance Leaf** | Irregular leaves from post-pruning regrowth |
| **Plucking Standard** | The number of leaves taken with the bud |
| **TBK** | Tea Board of Kenya |

### B. References

1. Tea Act 2020, Government of Kenya
2. Tea Board of Kenya Official Guidelines: https://www.teaboard.or.ke/
3. Farmer Power Training Repository: https://github.com/farmerpower-ai/farmer-power-training
4. Farmer Power Platform README: See `/README.md`
5. GitHub Issue #3 - Conditional Reject Support: https://github.com/farmerpower-ai/farmer-power-qc-analyzer/issues/3
6. GitHub Issue #20 - TBK Model Implementation: https://github.com/farmerpower-ai/farmer-power-training/issues/20

### C. Document History

| Version | Date       | Author           | Changes                                                                                                                                                             |
|---------|------------|------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1.0     | 2025-12-22 | Business Analyst | Initial specification                                                                                                                                               |
| 1.1     | 2025-12-22 | Business Analyst | Updated MarketGradingConfig to use `reject_conditions` + `conditional_reject` format compatible with QC Analyzer BinaryGradingSystem. Added dependency on issue #3. |
| 1.2     | 2026-01-05 | Business Analyst | Updated with real examples of leaf grading                                                                                                                          |

---

*This specification was created as part of the Farmer Power Platform project to support tea quality assessment in Kenya in compliance with TBK regulations.*