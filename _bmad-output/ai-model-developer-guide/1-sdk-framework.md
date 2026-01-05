# 1. SDK & Framework

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Agent Orchestration** | LangChain | Simple linear chains, prompt templates, output parsers |
| **Complex Workflows** | LangGraph | Stateful multi-step workflows, conditional branching, iterations |
| **LLM Gateway** | OpenRouter | Multi-provider access, model routing |
| **Vector DB** | Pinecone | RAG knowledge retrieval |
| **Event Bus** | DAPR Pub/Sub | Async communication with domain models |

## Framework Selection by Agent Type

| Agent Type | Framework | Rationale |
|------------|-----------|-----------|
| **Extractor** | LangChain | Linear workflow (fetch → extract → validate → output), no complex state needed |
| **Explorer** | LangGraph | Complex workflows - iterative analysis, conditional RAG, confidence-based re-analysis |
| **Generator** | LangGraph | Complex workflows - multiple outputs, prioritization, translation with quality checks |
| **Conversational** | LangGraph | Multi-turn dialogue requiring session state, context management, and channel routing |
| **Tiered-Vision** | LangGraph | Two-tier image processing with conditional routing - screen (Haiku) → diagnose (Sonnet) |

---

## Critical Principle: Configuration-Driven Agents (NO CODE Required)

> **⚠️ IMPORTANT: The 5 agent types above are GENERIC, REUSABLE PATTERNS implemented once in code. To create a new analysis or agent instance, you write ZERO Python code - only YAML configuration + prompts in MongoDB.**

### What This Means for Developers

| To Create... | You Need | Code Required? |
|--------------|----------|----------------|
| New disease analyzer | YAML config (`type: explorer`) + prompts | ❌ No |
| New data extractor | YAML config (`type: extractor`) + prompts | ❌ No |
| New content generator | YAML config (`type: generator`) + prompts | ❌ No |
| New chatbot persona | YAML config (`type: conversational`) + prompts | ❌ No |
| New image classifier | YAML config (`type: tiered-vision`) + prompts | ❌ No |

### Example: Adding "Weather Impact Analyzer"

```bash
# Step 1: Create configuration (NO CODE)
cat > config/agents/weather-impact-analyzer.yaml << EOF
agent:
  id: "weather-impact-analyzer"
  type: explorer                    # Reuses existing Explorer workflow
  version: "1.0.0"
  description: "Correlates quality issues with weather patterns"

  input:
    event: "collection.quality_event.created"
    schema:
      required: [doc_id, farmer_id, region]

  output:
    event: "ai.weather_analysis.complete"
    schema:
      fields: [correlation, confidence, weather_factors, recommendations]

  mcp_sources:
    - server: collection
      tools: [get_document, get_quality_events]
    - server: plantation
      tools: [get_weather_history, get_region_climate]

  llm:
    model: "anthropic/claude-3-5-sonnet"
    temperature: 0.3
    max_tokens: 1500

  rag:
    enabled: true
    knowledge_domains: [weather_patterns, tea_climate_sensitivity]
    top_k: 5
EOF

# Step 2: Add prompts to MongoDB (NO CODE)
fp-prompt-config deploy prompts/weather-analyzer.yaml

# Step 3: Deploy configuration (NO CODE)
fp-agent-config deploy config/agents/weather-impact-analyzer.yaml

# Result: New agent is live - ZERO lines of Python written
```

### When IS Code Required?

| Scenario | Code Required? |
|----------|----------------|
| New agent using existing type | ❌ No - YAML + prompts only |
| Changing prompts | ❌ No - MongoDB hot-reload |
| Switching LLM models | ❌ No - YAML only |
| Adding RAG knowledge | ❌ No - Pinecone + config |
| **New workflow pattern** (6th agent type) | ✅ Yes - new LangGraph workflow |
| **New MCP server** (new domain model) | ✅ Yes - new gRPC service |

**Rule:** The code examples in this guide show how the GENERIC workflows work. You don't copy/modify them for each new analysis - you configure instances via YAML.

---

## When to Use LangChain vs LangGraph

**Use LangChain when:**
- Workflow is strictly linear (A → B → C → D)
- No conditional branching required
- No iteration or retry loops needed
- Single output format

**Use LangGraph when:**
- Workflow has conditional branches
- Iterative refinement is needed (e.g., "not confident enough, retry with more context")
- Multiple parallel outputs required
- State needs to be tracked across steps
- Complex error recovery with alternative paths

## LangGraph Patterns

### Basic Graph Structure

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class ExplorerState(TypedDict):
    doc_id: str
    farmer_id: str
    document: dict
    farmer_context: dict
    rag_context: list[str]
    diagnosis: dict
    confidence: float
    iteration_count: int

def create_explorer_graph():
    workflow = StateGraph(ExplorerState)

    # Add nodes
    workflow.add_node("fetch_document", fetch_document_node)
    workflow.add_node("build_context", build_context_node)
    workflow.add_node("retrieve_rag", retrieve_rag_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("output", output_node)

    # Add edges
    workflow.set_entry_point("fetch_document")
    workflow.add_edge("fetch_document", "build_context")
    workflow.add_edge("build_context", "retrieve_rag")
    workflow.add_edge("retrieve_rag", "analyze")

    # Conditional edge based on confidence
    workflow.add_conditional_edges(
        "analyze",
        should_retry_or_output,
        {
            "retry": "retrieve_rag",  # Get more context and retry
            "output": "output"
        }
    )

    workflow.add_edge("output", END)

    return workflow.compile()

def should_retry_or_output(state: ExplorerState) -> str:
    if state["confidence"] < 0.7 and state["iteration_count"] < 3:
        return "retry"
    return "output"
```

### LangGraph Saga Pattern (Parallel Analyzers)

For complex analysis requiring multiple parallel analyzers with aggregation:

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.mongodb import MongoDBSaver
from typing import TypedDict, Optional
import asyncio

class SagaState(TypedDict):
    doc_id: str
    farmer_id: str
    triage_result: dict
    branch_results: dict[str, dict]  # Results from parallel branches
    primary_diagnosis: Optional[dict]
    secondary_diagnoses: list[dict]
    workflow_metadata: dict

def create_quality_analysis_saga():
    """
    Saga pattern for parallel analyzer orchestration.
    Used when triage confidence < 0.7 and multiple analyzers needed.
    """
    workflow = StateGraph(SagaState)

    # Nodes
    workflow.add_node("fetch_context", fetch_context_node)
    workflow.add_node("triage", triage_node)
    workflow.add_node("parallel_analyzers", parallel_analyzers_node)
    workflow.add_node("single_analyzer", single_analyzer_node)
    workflow.add_node("aggregate", aggregate_node)
    workflow.add_node("output", output_node)

    # Edges
    workflow.set_entry_point("fetch_context")
    workflow.add_edge("fetch_context", "triage")

    # Conditional: high confidence → single, low → parallel
    workflow.add_conditional_edges(
        "triage",
        route_by_confidence,
        {
            "single": "single_analyzer",
            "parallel": "parallel_analyzers"
        }
    )

    workflow.add_edge("single_analyzer", "aggregate")
    workflow.add_edge("parallel_analyzers", "aggregate")
    workflow.add_edge("aggregate", "output")
    workflow.add_edge("output", END)

    # Compile with MongoDB checkpointing for crash recovery
    checkpointer = MongoDBSaver.from_conn_string(
        conn_string=os.environ["MONGODB_URI"],
        db_name="ai_model",
        collection_name="workflow_checkpoints"
    )

    return workflow.compile(checkpointer=checkpointer)

def route_by_confidence(state: SagaState) -> str:
    """Route based on triage confidence."""
    if state["triage_result"]["confidence"] >= 0.7:
        return "single"
    return "parallel"

async def parallel_analyzers_node(state: SagaState) -> dict:
    """
    Fan-out to multiple analyzers in parallel.
    Implements timeout and partial failure handling.
    """
    triage = state["triage_result"]
    analyzers_to_run = triage["route_to"] + triage.get("also_check", [])

    # Create tasks for each analyzer
    tasks = {}
    for analyzer in analyzers_to_run:
        tasks[analyzer] = run_analyzer(analyzer, state)

    # Wait with timeout
    results = {}
    try:
        done, pending = await asyncio.wait(
            tasks.values(),
            timeout=30.0,  # 30 second timeout
            return_when=asyncio.ALL_COMPLETED
        )

        # Collect results
        for analyzer, task in tasks.items():
            if task in done:
                try:
                    results[analyzer] = task.result()
                except Exception as e:
                    results[analyzer] = {"error": str(e), "status": "failed"}
            else:
                task.cancel()
                results[analyzer] = {"error": "timeout", "status": "timeout"}

    except Exception as e:
        # Partial results are still useful
        pass

    return {"branch_results": results}

def aggregate_node(state: SagaState) -> dict:
    """
    Aggregate results from parallel analyzers.
    Select primary (highest confidence) and secondaries.
    """
    results = state["branch_results"]

    # Filter successful results
    successful = {
        k: v for k, v in results.items()
        if v.get("status") != "failed" and v.get("status") != "timeout"
    }

    if not successful:
        return {
            "primary_diagnosis": {"condition": "inconclusive", "confidence": 0},
            "secondary_diagnoses": []
        }

    # Sort by confidence
    sorted_results = sorted(
        successful.items(),
        key=lambda x: x[1].get("confidence", 0),
        reverse=True
    )

    primary = sorted_results[0][1]
    secondaries = [
        r[1] for r in sorted_results[1:]
        if r[1].get("confidence", 0) >= 0.5
    ][:2]  # Max 2 secondary

    return {
        "primary_diagnosis": primary,
        "secondary_diagnoses": secondaries
    }
```

### LangGraph Checkpointing (Crash Recovery)

Always use checkpointing for workflows that make LLM calls:

```python
from langgraph.checkpoint.mongodb import MongoDBSaver

def create_workflow_with_checkpointing():
    workflow = StateGraph(MyState)
    # ... add nodes and edges ...

    # MongoDB checkpointer survives crashes
    checkpointer = MongoDBSaver.from_conn_string(
        conn_string=os.environ["MONGODB_URI"],
        db_name="ai_model",
        collection_name="workflow_checkpoints"
    )

    return workflow.compile(checkpointer=checkpointer)

# When invoking, provide a thread_id for resumability
async def run_with_recovery(workflow, input_data: dict, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}

    # If workflow was interrupted, this resumes from last checkpoint
    result = await workflow.ainvoke(input_data, config)
    return result
```

**Crash Recovery Flow:**
```
1. Event received → workflow starts
2. Fetch context ✓ → checkpoint saved
3. Triage ✓ → checkpoint saved
4. Parallel analyzers running → CRASH!
5. AI Model restarts
6. Load checkpoint from MongoDB
7. Resume from last completed node
8. Re-run only incomplete branches
9. Continue to aggregation → output
```

### Generator Graph with Multiple Outputs

```python
class GeneratorState(TypedDict):
    farmer_id: str
    analyses: list[dict]
    farmer_context: dict
    prioritized_items: list[dict]
    detailed_report: str
    farmer_message: str
    message_language: str
    message_length: int
    translation_attempts: int

def create_generator_graph():
    workflow = StateGraph(GeneratorState)

    # Add nodes
    workflow.add_node("fetch_analyses", fetch_analyses_node)
    workflow.add_node("prioritize", prioritize_node)
    workflow.add_node("generate_report", generate_report_node)
    workflow.add_node("translate_message", translate_message_node)
    workflow.add_node("check_message_quality", check_message_quality_node)
    workflow.add_node("simplify_message", simplify_message_node)
    workflow.add_node("output", output_node)

    # Linear start
    workflow.set_entry_point("fetch_analyses")
    workflow.add_edge("fetch_analyses", "prioritize")
    workflow.add_edge("prioritize", "generate_report")
    workflow.add_edge("generate_report", "translate_message")
    workflow.add_edge("translate_message", "check_message_quality")

    # Conditional: message quality check
    workflow.add_conditional_edges(
        "check_message_quality",
        check_quality_result,
        {
            "too_long": "simplify_message",
            "quality_ok": "output"
        }
    )

    workflow.add_edge("simplify_message", "check_message_quality")
    workflow.add_edge("output", END)

    return workflow.compile()
```

### Conversational Agent Graph (Multi-Turn Dialogue)

The Conversational agent type handles interactive, multi-turn dialogue with users across different channels (voice, WhatsApp, SMS). It uses LangGraph for session state management and supports pluggable channel adapters.

**Architecture Overview:**

```
┌───────────────────────────────────────────────────────────────────┐
│                  CONVERSATIONAL AGENT PATTERN                      │
├───────────────────────────────────────────────────────────────────┤
│                                                                    │
│   Channel Input ──► Adapter ──► Conversation Engine ──► Response   │
│   (Voice/WhatsApp)    │              │                     │       │
│                       │              │                     │       │
│                       ▼              ▼                     ▼       │
│                   Normalize      LangGraph with       TTS/Text     │
│                   Input          Session State        Output       │
│                                                                    │
│   Session State: farmer_id, turn_count, context, history           │
│   Max Turns: 3-5 (cost control)                                    │
│   Max Duration: 3 minutes (voice)                                  │
│                                                                    │
└───────────────────────────────────────────────────────────────────┘
```

**Conversational State Definition:**

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.mongodb import MongoDBSaver
from typing import TypedDict, Optional, Literal
from datetime import datetime

class ConversationalState(TypedDict):
    # Session identification
    session_id: str
    farmer_id: str
    channel: Literal["voice", "whatsapp", "sms"]
    language: Literal["sw", "ki", "luo"]  # Swahili, Kikuyu, Luo

    # Conversation tracking
    turn_count: int
    max_turns: int  # Default: 5
    conversation_history: list[dict]  # [{role, content, timestamp}]

    # Current turn
    user_input: str  # Raw transcription or text
    user_intent: Optional[dict]  # Classified intent

    # Context from platform data
    farmer_context: Optional[dict]  # Latest quality, history, weather
    rag_context: list[str]  # Agronomic knowledge

    # Response generation
    response_text: str
    response_audio_url: Optional[str]  # For voice channel

    # Session management
    session_start: datetime
    should_end: bool  # True when max turns reached or user says goodbye


def create_conversational_graph():
    """
    LangGraph for multi-turn farmer dialogue.
    Supports voice quality advisor use case.
    """
    workflow = StateGraph(ConversationalState)

    # Add nodes
    workflow.add_node("identify_farmer", identify_farmer_node)
    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("fetch_context", fetch_context_node)
    workflow.add_node("retrieve_knowledge", retrieve_knowledge_node)
    workflow.add_node("generate_response", generate_response_node)
    workflow.add_node("synthesize_audio", synthesize_audio_node)
    workflow.add_node("update_history", update_history_node)
    workflow.add_node("end_session", end_session_node)

    # Entry point
    workflow.set_entry_point("identify_farmer")

    # Linear flow for context building
    workflow.add_edge("identify_farmer", "classify_intent")
    workflow.add_edge("classify_intent", "fetch_context")
    workflow.add_edge("fetch_context", "retrieve_knowledge")
    workflow.add_edge("retrieve_knowledge", "generate_response")

    # Conditional: voice channel needs audio synthesis
    workflow.add_conditional_edges(
        "generate_response",
        route_by_channel,
        {
            "voice": "synthesize_audio",
            "text": "update_history"
        }
    )

    workflow.add_edge("synthesize_audio", "update_history")

    # Conditional: continue or end session
    workflow.add_conditional_edges(
        "update_history",
        check_session_end,
        {
            "continue": END,  # Returns to await next user input
            "end": "end_session"
        }
    )

    workflow.add_edge("end_session", END)

    # Compile with MongoDB checkpointing for session persistence
    checkpointer = MongoDBSaver.from_conn_string(
        conn_string=os.environ["MONGODB_URI"],
        db_name="conversational_ai_model",
        collection_name="sessions"
    )

    return workflow.compile(checkpointer=checkpointer)


def route_by_channel(state: ConversationalState) -> str:
    """Route based on channel type."""
    if state["channel"] == "voice":
        return "voice"
    return "text"


def check_session_end(state: ConversationalState) -> str:
    """Determine if session should end."""
    if state["should_end"]:
        return "end"
    if state["turn_count"] >= state["max_turns"]:
        return "end"
    return "continue"
```

**Intent Classification Node (Fast - Haiku):**

```python
from src.llm.gateway import LLMGateway

async def classify_intent_node(state: ConversationalState) -> dict:
    """
    Fast intent classification using Haiku.
    Determines what the farmer is asking about.
    """
    from ai_model.config import settings

    llm = LLMGateway(settings=settings)

    system_prompt = """You are an intent classifier for farmer quality conversations.

Classify the farmer's message into one of these intents:
- quality_explanation: Asking why their quality was low/high
- improvement_advice: Asking how to improve quality
- weather_impact: Asking about weather effects on quality
- past_comparison: Asking about their historical performance
- greeting: Hello, starting conversation
- farewell: Goodbye, ending conversation
- clarification: Asking for more detail on previous response
- off_topic: Not related to tea quality

Respond in JSON: {"intent": "...", "confidence": 0.0-1.0, "entities": {...}}"""

    response = await llm.complete(
        model="anthropic/claude-3-haiku",  # Fast intent classification
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["user_input"]},
        ],
        max_tokens=150,
        temperature=0.1,
    )

    intent_result = json.loads(response.content)

    return {
        "user_intent": intent_result,
        "should_end": intent_result.get("intent") == "farewell"
    }
```

**Response Generation Node (Quality - Sonnet):**

```python
async def generate_response_node(state: ConversationalState) -> dict:
    """
    Generate personalized, data-grounded response.
    Uses Sonnet for quality reasoning.
    """
    from ai_model.config import settings

    llm = LLMGateway(settings=settings)

    # Build context from farmer data
    farmer = state.get("farmer_context", {})
    history = state.get("conversation_history", [])
    rag = state.get("rag_context", [])

    system_prompt = f"""You are a helpful tea quality advisor speaking to {farmer.get('name', 'the farmer')}.

PERSONA: Warm, encouraging, simple language (6th-grade level), Swahili-first.

CONVERSATION RULES:
- Reference THEIR specific data (not generic advice)
- Reference THEIR past successes when relevant
- Keep responses under 3 sentences for voice
- End with a question to guide the dialogue
- If you don't know, say so honestly

FARMER CONTEXT:
- Latest Grade: {farmer.get('latest_grade', 'unknown')}
- Primary %: {farmer.get('primary_pct', 'unknown')}%
- Top Issue: {farmer.get('top_issue', 'unknown')}
- Recent Weather: {farmer.get('weather_summary', 'unknown')}
- Past Best Grade: {farmer.get('best_grade', 'unknown')} on {farmer.get('best_grade_date', 'unknown')}

AGRONOMIC KNOWLEDGE:
{chr(10).join(rag) if rag else 'No specific knowledge retrieved.'}

CONVERSATION HISTORY:
{format_history(history)}

USER INTENT: {state.get('user_intent', {}).get('intent', 'unknown')}

Respond in the farmer's language ({state.get('language', 'sw')}).
"""

    response = await llm.complete(
        model="anthropic/claude-3-5-sonnet",  # Quality response generation
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["user_input"]},
        ],
        max_tokens=300,
        temperature=0.7,
    )

    return {"response_text": response.content}


def format_history(history: list[dict]) -> str:
    """Format conversation history for context."""
    if not history:
        return "No previous turns."

    formatted = []
    for turn in history[-4:]:  # Last 4 turns only (context window)
        role = "Farmer" if turn["role"] == "user" else "Advisor"
        formatted.append(f"{role}: {turn['content']}")

    return "\n".join(formatted)
```

**Voice Channel Adapter (Streaming Response):**

```python
from src.agents.types.conversational.adapters.base import ChannelAdapter
from src.notification.tts import TTSService
from src.notification.telephony import TelephonyService

class VoiceChatbotAdapter(ChannelAdapter):
    """
    Voice channel adapter with streaming response for natural conversation.
    Implements 3-phase output for perceived low latency.
    """

    def __init__(self, tts: TTSService, telephony: TelephonyService):
        self.tts = tts
        self.telephony = telephony

    async def send_response(
        self,
        session_id: str,
        response_text: str,
        language: str
    ) -> str:
        """
        Stream response in 3 phases for natural feel:
        1. Immediate acknowledgment
        2. Filler while processing
        3. Actual response
        """
        # Phase 1: Immediate acknowledgment (<0.5s)
        ack = self._get_acknowledgment(language)
        await self.telephony.play_audio(
            session_id,
            await self.tts.synthesize(ack, language)
        )

        # Phase 2: Filler if response is still generating
        # (In production, this runs in parallel with LLM)

        # Phase 3: Actual response
        audio_url = await self.tts.synthesize(
            response_text,
            language,
            speaking_rate=0.9  # Slightly slower for clarity
        )
        await self.telephony.play_audio(session_id, audio_url)

        return audio_url

    def _get_acknowledgment(self, language: str) -> str:
        """Quick acknowledgment phrases by language."""
        acks = {
            "sw": "Sawa, nimeelewa.",  # "OK, I understand"
            "ki": "Nĩ wega, nĩndĩraiguĩte.",  # Kikuyu equivalent
            "luo": "Ber, asewinjo.",  # Luo equivalent
        }
        return acks.get(language, acks["sw"])

    async def receive_input(self, session_id: str) -> str:
        """
        Receive and transcribe farmer speech.
        Uses Google Cloud Speech-to-Text for Swahili.
        """
        audio = await self.telephony.get_speech(
            session_id,
            timeout_seconds=10,
            silence_threshold_ms=2000  # End on 2s silence
        )

        transcript = await self.stt.transcribe(
            audio,
            language_code="sw-KE",  # Swahili (Kenya)
            model="latest_long"
        )

        return transcript


# Channel adapter registry (Open-Closed pattern)
CHANNEL_ADAPTERS = {
    "voice": VoiceChatbotAdapter,
    "whatsapp": WhatsAppChatAdapter,  # Future
    "sms": SMSChatAdapter,  # Future
}
```

**Conversational Agent Instance Configuration:**

```yaml
# src/agents/instances/conversational/farmer-voice-advisor.yaml
agent:
  id: "farmer-voice-advisor"
  type: conversational
  version: "1.0.0"
  description: "Voice-based quality advisor for farmers"

  channel:
    primary: voice
    languages: [sw, ki, luo]  # Swahili, Kikuyu, Luo
    tts_provider: google_cloud
    stt_provider: google_cloud

  session:
    max_turns: 5
    max_duration_seconds: 180  # 3 minutes
    timeout_seconds: 30  # Per-turn timeout

  llm:
    intent_classification:
      model: "anthropic/claude-3-haiku"   # Fast intent classification
      temperature: 0.1
      max_tokens: 150
    response_generation:
      model: "anthropic/claude-3-5-sonnet"   # Quality response generation
      temperature: 0.7
      max_tokens: 300

  mcp_sources:
    - server: collection
      tools: [get_farmer_documents, get_quality_events]
    - server: plantation
      tools: [get_farmer, get_weather_history]
    - server: knowledge
      tools: [get_diagnosis]

  rag:
    enabled: true
    knowledge_domains: [tea_quality, harvesting_best_practices]
    top_k: 3

  persona:
    style: "warm, encouraging, simple"
    reading_level: "6th grade"
    default_language: sw
    name: "Quality Advisor"

  fallback:
    on_stt_failure: "send_sms_with_details"
    on_timeout: "polite_goodbye"
    on_max_turns: "summarize_and_close"
```

---

### Tiered-Vision Agent Graph (Cost-Optimized Image Analysis)

The Tiered-Vision agent type handles cost-optimized image analysis by using a two-tier approach: fast screening with a cheap model, then conditional escalation to an expensive model only when needed.

**Architecture Overview:**

```
┌───────────────────────────────────────────────────────────────────┐
│                  TIERED-VISION AGENT PATTERN                       │
├───────────────────────────────────────────────────────────────────┤
│                                                                    │
│   Event ──► Fetch Thumbnail ──► Screen (Haiku) ──► Route          │
│                                       │                            │
│                    ┌──────────────────┼──────────────────┐        │
│                    ▼                  ▼                  ▼         │
│               "healthy"        "obvious_issue"    "needs_expert"   │
│                    │                  │                  │         │
│                    ▼                  ▼                  ▼         │
│              Skip (40%)      Haiku Only (25%)    Tier 2 (35%)     │
│                                                         │         │
│                                                         ▼         │
│                                    Fetch Original + RAG + Sonnet  │
│                                                         │         │
│                                                         ▼         │
│                                                   Deep Diagnosis   │
│                                                                    │
│   Cost Savings: 57% vs all-Sonnet approach                        │
│                                                                    │
└───────────────────────────────────────────────────────────────────┘
```

**Tiered-Vision State Definition:**

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.mongodb import MongoDBSaver
from typing import TypedDict, Optional, Literal

class TieredVisionState(TypedDict):
    # Input
    doc_id: str
    thumbnail_url: str
    original_url: str
    metadata: dict

    # Tier 1: Screening
    screen_result: Optional[dict]  # {classification, confidence, reason}
    screen_route: Literal["skip", "haiku_only", "tier2"]

    # Tier 2: Deep diagnosis (only populated if escalated)
    original_image: Optional[bytes]
    farmer_context: Optional[dict]
    rag_context: list[str]
    diagnosis: Optional[dict]

    # Output
    final_result: dict
    tier_used: Literal["tier1", "tier2"]
    cost_saved: bool  # True if Tier 2 was skipped


def create_tiered_vision_graph():
    """
    LangGraph for cost-optimized image analysis.
    57% cost savings by screening with Haiku first.
    """
    workflow = StateGraph(TieredVisionState)

    # Add nodes
    workflow.add_node("fetch_thumbnail", fetch_thumbnail_node)
    workflow.add_node("screen", screen_node)
    workflow.add_node("output_tier1", output_tier1_node)
    workflow.add_node("fetch_original", fetch_original_node)
    workflow.add_node("build_context", build_context_node)
    workflow.add_node("retrieve_rag", retrieve_rag_node)
    workflow.add_node("diagnose", diagnose_node)
    workflow.add_node("output_tier2", output_tier2_node)

    # Entry point
    workflow.set_entry_point("fetch_thumbnail")

    # Linear flow for Tier 1
    workflow.add_edge("fetch_thumbnail", "screen")

    # Conditional routing based on screen result
    workflow.add_conditional_edges(
        "screen",
        route_by_screen_result,
        {
            "skip": "output_tier1",           # Healthy - no diagnosis needed
            "haiku_only": "output_tier1",     # Obvious issue - Haiku sufficient
            "tier2": "fetch_original"         # Needs expert - escalate
        }
    )

    workflow.add_edge("output_tier1", END)

    # Tier 2 flow
    workflow.add_edge("fetch_original", "build_context")
    workflow.add_edge("build_context", "retrieve_rag")
    workflow.add_edge("retrieve_rag", "diagnose")
    workflow.add_edge("diagnose", "output_tier2")
    workflow.add_edge("output_tier2", END)

    # Compile with MongoDB checkpointing
    checkpointer = MongoDBSaver.from_conn_string(
        conn_string=os.environ["MONGODB_URI"],
        db_name="ai_model",
        collection_name="workflow_checkpoints"
    )

    return workflow.compile(checkpointer=checkpointer)


def route_by_screen_result(state: TieredVisionState) -> str:
    """Route based on Tier 1 screening result."""
    screen = state["screen_result"]
    classification = screen["classification"]
    confidence = screen["confidence"]

    if classification == "healthy" and confidence >= 0.85:
        return "skip"
    elif classification == "obvious_issue" and confidence >= 0.75:
        return "haiku_only"
    else:
        return "tier2"
```

**Tier 1: Screening Node (Haiku - Fast & Cheap):**

```python
async def screen_node(state: TieredVisionState) -> dict:
    """
    Fast screening using thumbnail and Haiku.
    Cost: ~$0.001/image
    """
    from ai_model.config import settings

    llm = LLMGateway(settings=settings)

    # Fetch thumbnail via Collection MCP
    thumbnail = await collection_mcp.get_document_thumbnail(state["doc_id"])

    system_prompt = """You are a tea leaf quality screening agent.

Analyze this thumbnail image and classify into one of these categories:
- "healthy": Leaf appears healthy, no visible issues
- "obvious_issue": Clear, easily identifiable problem (e.g., obvious disease, damage)
- "needs_expert": Ambiguous or complex issue requiring detailed analysis

Respond in JSON: {"classification": "...", "confidence": 0.0-1.0, "reason": "..."}"""

    response = await llm.complete(
        model="anthropic/claude-3-haiku",  # Fast, cheap screening
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "data": thumbnail}},
                    {"type": "text", "text": f"Metadata: {state.get('metadata', {})}"}
                ]
            },
        ],
        max_tokens=200,
        temperature=0.1,
    )

    screen_result = json.loads(response.content)

    return {"screen_result": screen_result}
```

**Tier 2: Deep Diagnosis Node (Sonnet - High Quality):**

```python
async def diagnose_node(state: TieredVisionState) -> dict:
    """
    Deep diagnosis using original image, farmer context, and RAG.
    Cost: ~$0.012/image
    Only called for 35% of images (needs_expert cases).
    """
    from ai_model.config import settings

    llm = LLMGateway(settings=settings)

    farmer = state.get("farmer_context", {})
    rag = state.get("rag_context", [])

    system_prompt = f"""You are an expert tea leaf disease diagnosis agent.

Analyze this full-resolution image with complete context to provide detailed diagnosis.

FARMER CONTEXT:
- Farm: {farmer.get('farm_name', 'unknown')}
- Region: {farmer.get('region', 'unknown')}
- Recent Weather: {farmer.get('weather_summary', 'unknown')}
- Historical Issues: {farmer.get('past_issues', [])}

AGRONOMIC KNOWLEDGE:
{chr(10).join(rag) if rag else 'No specific knowledge retrieved.'}

Provide diagnosis in JSON format:
{{
  "condition": "disease/pest/nutrient/environmental/handling",
  "specific_issue": "name of specific issue",
  "confidence": 0.0-1.0,
  "severity": "low/medium/high",
  "evidence": ["list of visual evidence"],
  "recommendations": ["list of actionable recommendations"],
  "requires_followup": true/false
}}"""

    response = await llm.complete(
        model="anthropic/claude-3-5-sonnet",  # High quality diagnosis
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "data": state["original_image"]}},
                    {"type": "text", "text": "Provide detailed diagnosis."}
                ]
            },
        ],
        max_tokens=1000,
        temperature=0.3,
    )

    diagnosis = json.loads(response.content)

    return {"diagnosis": diagnosis, "tier_used": "tier2", "cost_saved": False}
```

**Tiered-Vision Agent Instance Configuration:**

```yaml
# src/agents/instances/tiered-vision/leaf-quality-screen.yaml
agent:
  id: "leaf-quality-screen"
  type: tiered-vision
  version: "1.0.0"
  description: "Cost-optimized leaf quality image analysis"

  input:
    event: "collection.poor_quality_detected"
    schema:
      required: [doc_id, thumbnail_url]
      optional: [original_url, metadata]

  tier1:
    llm:
      model: "anthropic/claude-3-haiku"
      temperature: 0.1
      max_tokens: 200
    routing:
      healthy_threshold: 0.85      # Skip Tier 2 if confidence >= this
      obvious_threshold: 0.75      # Haiku-only if confidence >= this

  tier2:
    llm:
      model: "anthropic/claude-3-5-sonnet"
      temperature: 0.3
      max_tokens: 1000
    mcp_sources:
      - server: collection
        tools: [get_document, get_document_image]
      - server: plantation
        tools: [get_farmer, get_weather_history]
    rag:
      enabled: true
      knowledge_domains: [tea_diseases, pest_identification, nutrient_deficiency]
      top_k: 5

  output:
    event: "ai.diagnosis.complete"
    schema:
      condition: string
      confidence: number
      tier_used: enum
      cost_saved: boolean

  cost_optimization:
    expected_tier1_skip_rate: 0.40    # 40% healthy images
    expected_tier1_only_rate: 0.25    # 25% obvious issues
    expected_tier2_rate: 0.35         # 35% need expert analysis
    estimated_daily_savings: 57%       # vs all-Sonnet approach
```

---
