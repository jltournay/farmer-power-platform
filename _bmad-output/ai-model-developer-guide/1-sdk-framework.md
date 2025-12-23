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
    llm = LLMGateway(task_type="triage")  # Routes to Haiku

    intent_result = await llm.generate(
        system_prompt="""You are an intent classifier for farmer quality conversations.

Classify the farmer's message into one of these intents:
- quality_explanation: Asking why their quality was low/high
- improvement_advice: Asking how to improve quality
- weather_impact: Asking about weather effects on quality
- past_comparison: Asking about their historical performance
- greeting: Hello, starting conversation
- farewell: Goodbye, ending conversation
- clarification: Asking for more detail on previous response
- off_topic: Not related to tea quality

Respond in JSON: {"intent": "...", "confidence": 0.0-1.0, "entities": {...}}""",
        user_message=state["user_input"],
        max_tokens=150,
        temperature=0.1
    )

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
    llm = LLMGateway(task_type="generation")  # Routes to Sonnet

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

    response = await llm.generate(
        system_prompt=system_prompt,
        user_message=state["user_input"],
        max_tokens=300,
        temperature=0.7
    )

    return {"response_text": response}


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
      task_type: "triage"  # Haiku
      temperature: 0.1
      max_tokens: 150
    response_generation:
      task_type: "generation"  # Sonnet
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
