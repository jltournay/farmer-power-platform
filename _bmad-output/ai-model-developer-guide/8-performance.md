# 8. Performance

## Token Optimization

**Prompt efficiency:**

```python
# BAD - Verbose prompt
prompt = """
I would like you to please analyze the following document which contains
information about a farmer's tea leaf quality. The document was collected
from a QC Analyzer device at a tea factory. Please look at all the details
and provide your expert analysis...
"""

# GOOD - Concise prompt
prompt = """
Analyze this tea quality document and diagnose issues.

Document:
{document}

Provide: condition, confidence (0-1), severity, recommendations.
"""
```

**Context window management:**

```python
def truncate_context(context: str, max_tokens: int = 2000) -> str:
    """Truncate context to fit token budget."""

    # Estimate tokens (rough: 4 chars per token)
    estimated_tokens = len(context) / 4

    if estimated_tokens <= max_tokens:
        return context

    # Truncate with summary
    max_chars = max_tokens * 4
    truncated = context[:max_chars]

    return truncated + "\n\n[Context truncated for length]"
```

## Caching Strategies

**RAG cache:**

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def cached_rag_query(query_hash: str) -> list[str]:
    """Cache RAG results for repeated queries."""
    # Actual implementation fetches from Pinecone
    pass

def get_rag_context(query: str, domains: list[str]) -> list[str]:
    # Create cache key from query and domains
    cache_key = hashlib.md5(f"{query}:{sorted(domains)}".encode()).hexdigest()
    return cached_rag_query(cache_key)
```

**Embedding cache:**

```python
# Cache embeddings for repeated text
embedding_cache = {}

async def get_embedding(text: str) -> list[float]:
    cache_key = hashlib.md5(text.encode()).hexdigest()

    if cache_key not in embedding_cache:
        embedding_cache[cache_key] = await embedding_model.embed(text)

    return embedding_cache[cache_key]
```

## Batching Patterns

For scheduled jobs processing many items:

```python
async def process_farmers_batch(farmer_ids: list[str], batch_size: int = 10):
    """Process farmers in batches to manage load."""

    for i in range(0, len(farmer_ids), batch_size):
        batch = farmer_ids[i:i + batch_size]

        # Process batch concurrently
        tasks = [process_single_farmer(fid) for fid in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle results
        for farmer_id, result in zip(batch, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process {farmer_id}: {result}")
            else:
                await publish_result(farmer_id, result)

        # Rate limiting between batches
        await asyncio.sleep(1)
```

## Cost Monitoring

Track costs per agent and farmer:

```python
@dataclass
class LLMUsage:
    input_tokens: int
    output_tokens: int
    model: str
    cost_usd: float

async def track_llm_usage(
    agent_id: str,
    farmer_id: str,
    usage: LLMUsage
):
    """Track LLM usage for cost monitoring."""

    await metrics.record({
        "metric": "llm_usage",
        "agent_id": agent_id,
        "farmer_id": farmer_id,
        "model": usage.model,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cost_usd": usage.cost_usd,
        "timestamp": datetime.utcnow().isoformat()
    })
```

---
