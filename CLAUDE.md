# CLAUDE.md — Project Synapse

## What This Is

Single-user Windows desktop LLM chat client with invisible context management, document-aware RAG, and flow-state-preserving UX. This is a **private thinking environment**, not just a chatbot.

## Core Design Principles

1. **Flow State Preservation** — User's cognitive momentum is sacred. No interruptions, no visible resets.
2. **Strict Separation of Concerns** — Each layer does one thing. No leaky abstractions.
3. **RAG Correctness** — Retrieval must be precise, trustworthy, and context-aware.
4. **Low Overhead, High Inspectability** — Minimal resource usage; full transparency when requested.

## Known Failure Modes to Avoid

Claude Code must not:
- Introduce background agents, planners, or autonomous loops
- Allow the LLM to request retrieval directly (retrieval is orchestrator-initiated only)
- Collapse orchestrator logic into LLM adapters
- Store documents or embeddings inside conversation history
- Treat summaries as conversational prose instead of structured retrieval artifacts
- Merge or "simplify" distinct modules into fewer files without explicit approval
- Let intent signals affect retrieval scope, document selection, or summarization triggers
- Add "convenience" imports that create circular dependencies between layers

## Architecture (Strict Separation)

```
synapse/
├── ui/                    # PySide6 frontend ONLY. No business logic here.
│   ├── main_window.py     # Primary window, layout, chrome
│   ├── chat_panel.py      # Conversation display, streaming
│   ├── input_panel.py     # Text input, send button, hotkeys
│   ├── sidebar.py         # Model selector, document panel, settings
│   ├── inspector.py       # Prompt debugger sidebar (toggle-able)
│   └── dialogs.py         # Exit confirmation, artifact generation
│
├── orchestrator/          # Brain of the application
│   ├── prompt_builder.py  # Assembles final prompt. Does NOT call LLMs or trigger summarization.
│   ├── context_manager.py # Tracks tokens, detects thresholds. Does NOT generate summaries.
│   ├── intent_tracker.py  # Infers user mode. Does NOT affect retrieval or summarization.
│   └── waypoint_manager.py# Stores/retrieves waypoints. Does NOT decide when to summarize.
│
├── storage/               # All persistence and retrieval
│   ├── vector_store_client.py  # Abstract interface (FAISS default, swappable)
│   ├── conversation_store.py   # .jsonl archive management
│   ├── retrieval_blacklist.py  # Topic-based exclusion rules
│   └── document_indexer.py     # Chunking, embedding, parent-doc mapping
│
├── summarization/         # Context compression
│   ├── summary_generator.py    # XML summary creation
│   ├── waypoint_handler.py     # Respect user-marked anchors
│   └── drift_detector.py       # Semantic shift detection (chaptering)
│
├── llm/                   # API adapters (stateless)
│   ├── base_adapter.py    # Abstract interface
│   ├── anthropic_adapter.py
│   ├── openai_adapter.py
│   └── openrouter_adapter.py
│
├── config/                # Configuration
│   ├── settings.py        # App settings, paths, defaults
│   ├── models.py          # Model definitions, token limits, pricing
│   └── themes.py          # Dark theme colors, fonts
│
└── utils/                 # Shared utilities
    ├── token_counter.py   # Model-aware token counting
    ├── logging.py         # Structured logging
    └── encryption.py      # Local data encryption (optional)
```

## Behavioral Constraints

### Intent Signals
Intent signals (analysis, drafting, exploration, adversarial) may influence **tone, verbosity, and reasoning depth only**. They must never affect:
- Retrieval scope or ranking
- Document selection
- Summarization triggers or boundaries
- RAG chunk filtering

### Layer Boundaries
- **UI** calls **Orchestrator**. Never calls LLM or Storage directly.
- **Orchestrator** calls **Storage**, **Summarization**, and **LLM**. Coordinates, does not implement.
- **Storage** is called by Orchestrator only. Never initiates actions.
- **LLM** adapters are stateless. They receive a prompt, return a response. No memory, no retrieval.
- **Summarization** is triggered by Orchestrator. Never self-triggers.

## Key Abstractions

### vector_store_client.py
All retrieval goes through this interface. FAISS is the default implementation.

```python
class VectorStoreClient(ABC):
    def index(self, chunks: List[Chunk], metadata: Dict) -> None: ...
    def query(self, query: str, k: int = 5) -> List[RetrievalResult]: ...
    def delete(self, doc_id: str) -> None: ...
    def get_parent(self, chunk_id: str) -> Optional[ParentDocument]: ...
```

Swapping to Chroma or another store must be a one-file change. Never let FAISS-specific assumptions leak into orchestrator or LLM layers.

### prompt_builder.py
Deterministic, inspectable prompt assembly:

```
[SYSTEM PROMPT]
[SUMMARY BLOCK (if context was compressed)]
[RAG CONTEXT (with confidence scores, invisible to user)]
[INTENT SIGNAL (low-priority mode hint)]
[CONVERSATION HISTORY]
[CURRENT USER MESSAGE]
```

### context_manager.py
Triggers summarization based on:
1. Token count approaching 80% of model's context window
2. Semantic drift detection (topic shift from conversation centroid)
3. User-placed waypoints (explicit summarization anchors)

## Data Formats

### XML Summary Structure
```xml
<ContextSummary>
    <GeneralSubject>...</GeneralSubject>
    <SpecificContext>
        <Subtopic>...</Subtopic>
        <Entities>...</Entities>
        <KeyPoints>...</KeyPoints>
    </SpecificContext>
    <NextExpectedTopics>...</NextExpectedTopics>
    <UserIntent mode="analysis|drafting|exploration|adversarial">...</UserIntent>
</ContextSummary>
```

### Conversation Archive (.jsonl)
Each line is a complete session record:
```json
{
    "session_id": "uuid",
    "started_at": "ISO8601",
    "ended_at": "ISO8601",
    "models_used": ["claude-sonnet-4-20250514", "gpt-4o"],
    "summary_xml": "<ContextSummary>...</ContextSummary>",
    "token_count": 45000,
    "drift_events": 3,
    "waypoints": [{"index": 42, "created_at": "ISO8601"}],
    "artifacts_generated": ["outline", "decision_log"]
}
```

### RAG Chunk Metadata
```json
{
    "chunk_id": "uuid",
    "parent_id": "uuid",
    "source_file": "document.pdf",
    "page_or_section": "Section 3.2",
    "similarity_score": 0.87,
    "recency_weight": 0.95,
    "source_weight": 1.0,
    "blacklisted_topics": ["deprecated_api"]
}
```

## Conventions

- **API keys**: Load from environment variables only (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_KEY`, `GABAI_KEY`)
- **Token counting**: Use tiktoken for OpenAI models, anthropic's counter for Claude
- **Embedding model**: Default to `text-embedding-3-small` for cost/performance balance
- **File paths**: Use `pathlib.Path` everywhere, never raw strings
- **Async**: Use `asyncio` for LLM calls; UI runs on Qt's event loop
- **Logging**: Structured JSON logs to `~/.synapse/logs/`

## Non-Goals (Hard Constraints)

These are NOT features we forgot. They are explicitly excluded:

- ❌ **No agents or autonomous tool use** — Synapse retrieves and synthesizes, it does not act
- ❌ **No multi-user support** — Single user, local machine only
- ❌ **No SaaS or cloud backend** — All data stays local
- ❌ **No background services** — App runs when open, stops when closed
- ❌ **No plugin system** — Extensibility through code, not runtime plugins

## RAG Design Decisions

### Hybrid Retrieval (Vector + BM25)
Pure vector search fails on:
- Error codes and stack traces
- Acronyms and abbreviations
- Code identifiers and function names
- Proper nouns and technical terms

Solution: Combine FAISS dense retrieval with BM25 keyword search using Reciprocal Rank Fusion (RRF).

### Parent-Document Retrieval
Index small chunks (512 tokens) for precise recall, but return the parent block (page, function, section) to prevent fragment-level hallucination.

### Confidence-Weighted Injection
Each retrieved chunk carries metadata:
- `similarity_score`: Vector distance
- `recency_weight`: How recently the source was added/referenced
- `source_weight`: User-configurable trust level per document

This metadata goes to the system prompt only. The LLM reasons about reliability; the user sees clean responses.

## Git Discipline

- **Commit after each working increment** — If it runs, commit it
- **Push to origin/main before ending a session** — Never leave work only on local
- **Meaningful commit messages** — Reference the feature/fix: `feat(rag): add parent-document retrieval`
- **Branch for experiments** — `git checkout -b experiment/vision-rag`

## Debugging Heuristics

| Symptom | First Place to Check |
|---------|---------------------|
| Token count wrong | `orchestrator/context_manager.py`, `utils/token_counter.py` |
| RAG returning garbage | Embedding dimensions mismatch in `storage/vector_store_client.py` |
| Summaries losing info | `summarization/summary_generator.py` prompt template |
| UI not updating | Signal/slot connections in `ui/main_window.py` |
| Drift triggering too often | Threshold tuning in `summarization/drift_detector.py` |
| Model switching fails | API key loading in `llm/*_adapter.py` |
| Blacklist not working | Topic matching logic in `storage/retrieval_blacklist.py` |

## Testing Strategy

- **Unit tests**: Each module in isolation, mock external dependencies
- **Integration tests**: Full prompt assembly → LLM call → response parsing
- **RAG tests**: Known document → known query → expected chunks retrieved
- **UI tests**: Qt's QTest framework for input handling and display

## Performance Targets

- **Cold start**: < 3 seconds to input-ready state
- **Message send to first token**: < 500ms (network permitting)
- **RAG query**: < 200ms for 10k document corpus
- **Summarization**: Background thread, never blocks UI

## Session Checklist for Claude Code

Before ending any coding session:

1. ✅ Code compiles/runs without errors
2. ✅ New functionality has basic test coverage
3. ✅ Changes committed with descriptive message
4. ✅ Pushed to `https://github.com/roanwave/synapse`
5. ✅ Updated this file if architecture changed
6. ✅ No layer boundary violations introduced
7. ✅ No modules merged without explicit approval
