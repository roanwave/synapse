# Phase 1 Prompt for Claude Code

Copy and paste this prompt into Claude Code to begin Phase 1 development.

---

## PROMPT START

I'm building **Synapse**, a single-user Windows desktop LLM chat application. This is Phase 1: Foundation & Single-Model Chat.

### Repository

Clone or initialize at: `https://github.com/roanwave/synapse`

### First Task: Create CLAUDE.md

Before writing any code, create the `CLAUDE.md` file at the repository root. This file will guide all future development. Here is the complete content:

```markdown
# CLAUDE.md — Project Synapse

## What This Is

Single-user Windows desktop LLM chat client with invisible context management, document-aware RAG, and flow-state-preserving UX. This is a **private thinking environment**, not just a chatbot.

## Core Design Principles

1. **Flow State Preservation** — User's cognitive momentum is sacred. No interruptions, no visible resets.
2. **Strict Separation of Concerns** — Each layer does one thing. No leaky abstractions.
3. **RAG Correctness** — Retrieval must be precise, trustworthy, and context-aware.
4. **Low Overhead, High Inspectability** — Minimal resource usage; full transparency when requested.

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
│   ├── prompt_builder.py  # Deterministic assembly: system + summary + RAG + conversation
│   ├── context_manager.py # Token tracking, drift detection, summarization triggers
│   ├── intent_tracker.py  # Silent mode inference (analysis/drafting/exploration)
│   └── waypoint_manager.py# Soft checkpoints for summarization boundaries
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

## Non-Goals (Hard Constraints)

- ❌ **No agents or autonomous tool use**
- ❌ **No multi-user support**
- ❌ **No SaaS or cloud backend**
- ❌ **No background services**

## Git Discipline

- Commit after each working increment
- Push to origin/main before ending a session
- Meaningful commit messages referencing the feature/fix
```

### Phase 1 Requirements

Create a minimal but functional chat application with:

#### 1. Project Structure

Create the directory structure from CLAUDE.md. For Phase 1, we only need:
- `main.py` (entry point)
- `ui/main_window.py`, `ui/chat_panel.py`, `ui/input_panel.py`
- `llm/base_adapter.py`, `llm/anthropic_adapter.py`
- `orchestrator/prompt_builder.py`
- `config/settings.py`, `config/themes.py`
- `utils/token_counter.py`
- `requirements.txt`

#### 2. UI Requirements (PySide6)

- **Main window**: 1000x700 default size, resizable
- **Chat panel**: Scrollable area displaying conversation history
  - User messages aligned right, assistant messages aligned left
  - Support streaming (text appears as it arrives)
- **Input panel**: 
  - Multi-line text field at bottom
  - Send button (also triggered by Ctrl+Enter)
  - **Input field must have focus on app launch**
- **Dark theme**: Apply a dark color scheme (not default Qt gray)
  - Background: #1a1a2e or similar dark blue-gray
  - Text: #e0e0e0
  - Accent: #4a9eff or similar blue
  - User message bubbles: slightly lighter than background
  - Assistant message bubbles: slightly different shade

#### 3. LLM Integration

- Load `ANTHROPIC_API_KEY` from environment variable
- Use Claude Sonnet (claude-sonnet-4-20250514) as the default model
- Implement streaming responses
- Handle errors gracefully (show in UI, don't crash)

#### 4. Basic Orchestration

- `prompt_builder.py`: Assemble system prompt + conversation history
- Simple system prompt: "You are a helpful assistant."
- Maintain conversation history in memory (no persistence yet)

#### 5. Token Counter

- Display current token count somewhere visible (e.g., status bar or near input)
- Use tiktoken or anthropic's tokenizer
- Update after each message exchange

#### 6. requirements.txt

```
PySide6>=6.6.0
anthropic>=0.18.0
tiktoken>=0.5.0
python-dotenv>=1.0.0
```

### Acceptance Criteria

Before considering Phase 1 complete, verify:

1. [ ] `python main.py` launches the application
2. [ ] Input field has focus immediately on launch
3. [ ] Can type a message and send it (button or Ctrl+Enter)
4. [ ] Response streams into the chat panel
5. [ ] Conversation history is maintained within the session
6. [ ] Token count displays and updates
7. [ ] Dark theme is applied (not default gray)
8. [ ] No crashes on API errors (graceful handling)

### Git Checkpoint

After Phase 1 is working:

```bash
git add .
git commit -m "feat: Phase 1 complete - basic chat with Claude Sonnet"
git push origin main
```

**IMPORTANT**: Always push to the remote repository before ending the session.

### Code Style Notes

- Use type hints throughout
- Use `pathlib.Path` for file paths
- Async for LLM calls (`asyncio` + `qasync` for Qt integration)
- Keep UI code in `ui/` — no business logic there
- Keep LLM code in `llm/` — stateless adapters only

### Do Not Include Yet

These are for later phases:
- Model switching dropdown
- RAG/document handling
- Summarization
- Settings persistence
- Exit confirmation dialog

Focus only on the core chat loop working smoothly.

---

## PROMPT END
