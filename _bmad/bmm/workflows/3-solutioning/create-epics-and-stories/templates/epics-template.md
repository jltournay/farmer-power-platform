---
stepsCompleted: []
inputDocuments: []
---

# {{project_name}} - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for {{project_name}}, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

{{fr_list}}

### NonFunctional Requirements

{{nfr_list}}

### Additional Requirements

{{additional_requirements}}

### FR Coverage Map

{{requirements_coverage_map}}

## Epic List

{{epics_list}}

<!-- Repeat for each epic in epics_list (N = 1, 2, 3...) -->

## Epic {{N}}: {{epic_title_N}}

{{epic_goal_N}}

### Use Cases

<!-- Define use cases ONLY for epics involving multi-step user workflows or multi-service pipelines -->
<!-- Use cases remain functional: describe what the actor does and what the system responds -->
<!-- No technical implementation details (no service names, no API endpoints, no database operations) -->

#### UC{{N}}.1: {{use_case_title}}

**Actor:** {{actor}}
**Preconditions:** {{preconditions}}
**Main Flow:**

1. {{actor_action_1}} → {{system_response_1}}
2. {{actor_action_2}} → {{system_response_2}}
3. {{actor_action_N}} → {{system_response_N}}

**Postcondition:** {{end_state_functional_outcome}}

<!-- Repeat UC for each distinct user workflow in this epic -->

### Stories

<!-- Repeat for each story (M = 1, 2, 3...) within epic N -->

### Story {{N}}.{{M}}: {{story_title_N_M}}

As a {{user_type}},
I want {{capability}},
So that {{value_benefit}}.

**Acceptance Criteria:**

<!-- for each AC on this story -->

**Given** {{precondition}}
**When** {{action}}
**Then** {{expected_outcome}}
**And** {{additional_criteria}}

<!-- End story repeat -->
