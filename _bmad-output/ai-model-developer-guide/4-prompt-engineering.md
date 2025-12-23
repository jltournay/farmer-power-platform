# 4. Prompt Engineering

## Prompt Structure Standards

### System Prompt Structure

```markdown
# Role Definition
You are a [specific role] for the Farmer Power platform.

# Core Responsibility
Your task is to [clear, specific responsibility].

# Guidelines
1. [Specific guideline 1]
2. [Specific guideline 2]
3. [Specific guideline 3]

# Constraints
- DO NOT [constraint 1]
- DO NOT [constraint 2]
- ALWAYS [requirement]

# Output Format
Respond in [format] with the following structure:
[schema or example]

# Examples (if needed)
# Example 1
Input: [example input]
Output: [example output]
```

### Template Prompt Structure

```markdown
# Context Section 1
{{variable_1}}

# Context Section 2
{{variable_2}}

# Task
[Clear instruction of what to do with the context]

# Additional Instructions (if needed)
[Specific instructions for this request]
```

## Output Format Enforcement

Always use structured output when possible:

```python
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

class DiagnosisOutput(BaseModel):
    condition: str = Field(description="Identified condition")
    confidence: float = Field(ge=0, le=1, description="Confidence score")
    severity: str = Field(description="low, moderate, high, or critical")
    details: str = Field(description="Detailed explanation")
    recommendations: list[str] = Field(description="List of recommendations")

parser = PydanticOutputParser(pydantic_object=DiagnosisOutput)

# Include format instructions in prompt
prompt = f"""
{system_prompt}

{parser.get_format_instructions()}

{template_with_context}
"""
```

## Few-Shot Examples

Use few-shot examples for complex outputs:

```markdown
# Examples

# Example 1: Fungal Infection
Input:
- Grade: D
- Quality issues: leaf spots, discoloration
- Season: October (rainy)

Output:
{
  "condition": "fungal_infection",
  "confidence": 0.85,
  "severity": "moderate",
  "details": "Leaf spots and discoloration during rainy season consistent with Cercospora leaf spot",
  "recommendations": ["Apply copper-based fungicide", "Improve drainage", "Remove affected leaves"]
}

# Example 2: Moisture Issues
Input:
- Grade: C
- Quality issues: excessive moisture
- Time: Early morning harvest

Output:
{
  "condition": "harvest_timing_issue",
  "confidence": 0.92,
  "severity": "low",
  "details": "Excessive moisture from early morning harvest before dew evaporation",
  "recommendations": ["Delay harvest until after 9 AM", "Ensure proper withering time"]
}
```

## Externalized Prompt Management

Prompts are stored in MongoDB for hot-reload capability and A/B testing without redeployment. Source files in Git provide version control and review workflow.

### Prompt Source File Structure

```yaml
# src/prompts/explorers/disease-diagnosis/prompt.yaml
prompt:
  prompt_id: "disease-diagnosis"
  agent_id: "diagnose-quality-issue"
  version: "2.1.0"

  content:
    system_prompt: |
      You are an expert agricultural diagnostician for the Farmer Power platform.

      Your role is to analyze quality issues in tea leaf samples and provide
      accurate diagnoses with actionable recommendations.

      ## Guidelines
      - Be specific and actionable
      - Include confidence levels (0-1)
      - Consider regional and seasonal factors
      - Prioritize farmer-friendly language

      ## Output Format
      Respond in JSON with: condition, confidence, severity, details, recommendations

    template: |
      ## Input Document
      {{document}}

      ## Farmer Context
      {{farmer_context}}

      ## Expert Knowledge
      {{rag_context}}

      ## Task
      Analyze the above information and diagnose any quality issues.

    output_schema:
      type: object
      properties:
        condition: { type: string }
        confidence: { type: number, minimum: 0, maximum: 1 }
        severity: { type: string, enum: [low, moderate, high, critical] }
        details: { type: string }
        recommendations: { type: array, items: { type: string } }

  metadata:
    author: "agronomist_team"
    changelog:
      - "2.1.0: Added regional context consideration"
      - "2.0.0: Restructured output format"
      - "1.0.0: Initial version"
```

### Runtime Prompt Loading

Agents load prompts from MongoDB at startup with automatic refresh:

```python
class PromptManager:
    """Manage prompt loading from MongoDB with caching."""

    def __init__(self, db_client, refresh_interval: int = 300):
        self.db = db_client
        self.cache = {}
        self.refresh_interval = refresh_interval  # 5 minutes default

    async def get_prompt(
        self,
        prompt_id: str,
        version: str = None
    ) -> PromptConfig:
        """
        Load prompt from MongoDB.
        Uses cache with TTL for performance.
        """
        cache_key = f"{prompt_id}:{version or 'active'}"

        # Check cache
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached["loaded_at"] < self.refresh_interval:
                return cached["prompt"]

        # Load from MongoDB
        query = {"prompt_id": prompt_id}
        if version:
            query["version"] = version
        else:
            query["status"] = "active"

        doc = await self.db.prompts.find_one(query)

        if not doc:
            raise PromptNotFoundError(f"Prompt {prompt_id} not found")

        prompt = PromptConfig(
            system_prompt=doc["content"]["system_prompt"],
            template=doc["content"]["template"],
            output_schema=doc["content"].get("output_schema"),
            few_shot_examples=doc["content"].get("few_shot_examples", []),
            version=doc["version"],
            ab_test=doc.get("ab_test")
        )

        # Update cache
        self.cache[cache_key] = {
            "prompt": prompt,
            "loaded_at": time.time()
        }

        return prompt

    async def force_refresh(self, prompt_id: str):
        """Force immediate refresh of a prompt (for A/B test changes)."""
        keys_to_delete = [k for k in self.cache if k.startswith(f"{prompt_id}:")]
        for key in keys_to_delete:
            del self.cache[key]
```

### Prompt Deployment Workflow

```
┌───────────────────────────────────────────────────────────────────┐
│                   PROMPT DEPLOYMENT WORKFLOW                       │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. AUTHOR (Local Development)                                    │
│     └─→ Edit prompt YAML in src/prompts/                         │
│     └─→ Test locally with farmer-cli playground                  │
│     └─→ Commit to Git (status: draft)                            │
│                                                                   │
│  2. REVIEW (Pull Request)                                         │
│     └─→ PR triggers validation: farmer-cli prompt validate       │
│     └─→ Reviewer checks prompt quality, examples, schema         │
│     └─→ Approval merges to main                                  │
│                                                                   │
│  3. STAGE (CI/CD Pipeline)                                        │
│     └─→ farmer-cli prompt stage --prompt disease-diagnosis       │
│     └─→ Uploads to MongoDB with status: staged                   │
│     └─→ Runs golden sample tests against staged version          │
│                                                                   │
│  4. A/B TEST (Optional)                                           │
│     └─→ farmer-cli prompt ab-test start --prompt disease-diagnosis │
│     └─→ Routes 10-20% traffic to staged version                  │
│     └─→ Monitors accuracy and latency metrics                    │
│                                                                   │
│  5. PROMOTE                                                       │
│     └─→ farmer-cli prompt promote --prompt disease-diagnosis     │
│     └─→ Archives previous active version                         │
│     └─→ Sets staged → active (immediate, no redeploy)            │
│                                                                   │
│  6. ROLLBACK (If Needed)                                          │
│     └─→ farmer-cli prompt rollback --prompt disease-diagnosis    │
│     └─→ Restores previous archived version to active             │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### CLI Commands for Prompt Management

```bash
# Validate prompt YAML structure
farmer-cli prompt validate --prompt disease-diagnosis

# Stage prompt to MongoDB (from Git source)
farmer-cli prompt stage --prompt disease-diagnosis

# Start A/B test with staged version
farmer-cli prompt ab-test start \
  --prompt disease-diagnosis \
  --traffic 20

# Check A/B test results
farmer-cli prompt ab-test status --prompt disease-diagnosis

# Promote staged to active
farmer-cli prompt promote --prompt disease-diagnosis

# Rollback to previous version
farmer-cli prompt rollback \
  --prompt disease-diagnosis \
  --to-version 2.0.0

# List all versions
farmer-cli prompt versions --prompt disease-diagnosis

# Force refresh in running AI Model (immediate)
farmer-cli prompt refresh --prompt disease-diagnosis --env production
```

### Prompt A/B Testing

Test prompt changes with production traffic before full rollout:

```python
class PromptABTestRouter:
    """Route to control or variant prompt versions."""

    def __init__(self, test_config: dict):
        self.prompt_id = test_config["prompt_id"]
        self.control_version = test_config["control_version"]
        self.variant_version = test_config["variant_version"]
        self.traffic_percentage = test_config["traffic_percentage"]

    def get_version(self, request_id: str) -> tuple[str, str]:
        """
        Deterministic routing based on request_id.
        Returns (version, group) tuple.
        """
        hash_val = int(hashlib.md5(request_id.encode()).hexdigest(), 16)
        bucket = hash_val % 100

        if bucket < self.traffic_percentage:
            return self.variant_version, "variant"
        return self.control_version, "control"

    async def get_prompt_with_tracking(
        self,
        prompt_manager: PromptManager,
        request_id: str
    ) -> PromptConfig:
        """Get prompt version with A/B tracking."""
        version, group = self.get_version(request_id)

        prompt = await prompt_manager.get_prompt(
            self.prompt_id,
            version=version
        )

        # Track for analysis
        await metrics.record_ab_usage(
            prompt_id=self.prompt_id,
            version=version,
            group=group,
            request_id=request_id
        )

        return prompt
```

### Key Benefits

| Benefit | Description |
|---------|-------------|
| **No Redeploy** | Change prompts without rebuilding/deploying AI Model container |
| **Hot Reload** | 5-minute cache TTL means changes take effect quickly |
| **A/B Testing** | Test prompt changes safely with subset of traffic |
| **Instant Rollback** | Restore previous version in seconds if issues arise |
| **Version History** | Full audit trail of all prompt changes |
| **Git-Backed** | Source of truth in Git with review workflow |

---
