# 6. Error Handling

## Error Categories

| Category | Examples | Handling |
|----------|----------|----------|
| **Transient** | Rate limit, timeout, network | Retry with backoff |
| **LLM Output** | Invalid JSON, missing fields | Parse error → retry with guidance |
| **Data** | Missing document, invalid farmer_id | Publish error event |
| **System** | MCP unavailable, RAG down | Circuit breaker → fallback |

## Retry Strategy

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class TransientError(Exception):
    """Errors that should be retried."""
    pass

class DataError(Exception):
    """Errors in input data - do not retry."""
    pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=0.1, max=2),
    retry=retry_if_exception_type(TransientError)
)
async def call_llm_with_retry(prompt: str, config: dict):
    try:
        response = await llm_gateway.complete(prompt, config)
        return parse_response(response)
    except RateLimitError:
        raise TransientError("Rate limited")
    except TimeoutError:
        raise TransientError("Request timed out")
    except InvalidResponseError as e:
        # Try once more with format reminder
        if "retry_count" not in config:
            config["retry_count"] = 1
            config["format_reminder"] = True
            raise TransientError("Invalid response format")
        raise DataError(f"LLM cannot produce valid output: {e}")
```

## LLM Output Repair

When LLM produces invalid output, try to repair:

```python
def parse_with_repair(response: str, schema: dict) -> dict:
    """Parse LLM response with automatic repair attempts."""

    # Attempt 1: Direct parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Attempt 2: Extract JSON from markdown code block
    json_match = re.search(r'```json?\s*([\s\S]*?)\s*```', response)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Attempt 3: Ask LLM to fix its output
    repair_prompt = f"""
    The following output is not valid JSON:
    {response}

    Please provide the same information as valid JSON matching this schema:
    {json.dumps(schema)}
    """

    repaired = llm_gateway.complete(repair_prompt, {"temperature": 0})
    return json.loads(repaired)
```

## Dead Letter Handling

Failed events go to dead letter topic for investigation:

```python
async def handle_agent_error(event: dict, error: Exception, context: dict):
    """Handle unrecoverable errors."""

    dead_letter_event = {
        "original_event": event,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "stack_trace": traceback.format_exc(),
        "agent_id": context["agent_id"],
        "timestamp": datetime.utcnow().isoformat(),
        "retry_count": context.get("retry_count", 0)
    }

    await dapr_publisher.publish(
        topic="ai.errors.dead_letter",
        payload=dead_letter_event
    )

    # Also log for alerting
    logger.error(
        "Agent failed after retries",
        extra={
            "agent_id": context["agent_id"],
            "error": str(error),
            "event_id": event.get("id")
        }
    )
```

---
