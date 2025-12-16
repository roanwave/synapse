# Synapse Development Phase Plan

## Overview

This plan breaks Synapse development into four phases, each producing a working increment. Features are tiered by priority based on the "force multiplier" principle: high-leverage additions that deepen power without breaking flow, scope, or architectural discipline.

---

## Phase 1: Foundation & Single-Model Chat

**Goal**: Scaffold the project, establish architecture, get a basic chat working end-to-end.

### Deliverables

1. **Project structure** matching `CLAUDE.md` architecture
2. **PySide6 window** with:
   - Input field (auto-focused on launch)
   - Send button
   - Conversation display (streaming support)
   - Basic dark theme applied
3. **Single model working** (Claude Sonnet via Anthropic API)
4. **Token counter** functional and displayed
5. **CLAUDE.md** in repo root

### Key Files to Create

```
synapse/
├── CLAUDE.md
├── requirements.txt
├── main.py
├── ui/
│   ├── __init__.py
│   ├── main_window.py
│   ├── chat_panel.py
│   └── input_panel.py
├── llm/
│   ├── __init__.py
│   ├── base_adapter.py
│   └── anthropic_adapter.py
├── orchestrator/
│   ├── __init__.py
│   └── prompt_builder.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── themes.py
└── utils/
    ├── __init__.py
    └── token_counter.py
```

### Acceptance Criteria

- [ ] App launches, input field has focus
- [ ] User can type message, press Enter or click Send
- [ ] Response streams into conversation panel
- [ ] Token count updates after each exchange
- [ ] Dark theme applied (not default Qt gray)

### Git Checkpoint

```bash
git add .
git commit -m "feat: Phase 1 complete - basic chat with Claude Sonnet"
git push origin main
```

---

## Phase 2: Multi-Model + Context Management

**Goal**: Add model switching, implement invisible context compression, add core "thinking environment" features.

### Deliverables

1. **Model dropdown** with:
   - Anthropic models (Claude Sonnet, Claude Opus)
   - OpenAI models (GPT-4o, GPT-4-turbo)
   - OpenRouter models (configurable list)
2. **Context management**:
   - 80% token threshold detection
   - XML summary generation
   - Seamless prompt reconstruction with summary injection
3. **Semantic drift detection** (topic-shift triggers)
4. **Conversation waypoints** (user-placed summarization anchors)
5. **Silent intent tracking** (mode inference: analysis/drafting/exploration)
6. **Regenerate last response** (re-roll with same or different model)

### Key Files to Create/Modify

```
├── ui/
│   └── sidebar.py              # NEW: Model selector, settings
├── llm/
│   ├── openai_adapter.py       # NEW
│   └── openrouter_adapter.py   # NEW
├── orchestrator/
│   ├── context_manager.py      # NEW: Token tracking, thresholds
│   ├── intent_tracker.py       # NEW: Mode inference
│   └── waypoint_manager.py     # NEW: Checkpoint management
├── summarization/
│   ├── __init__.py             # NEW
│   ├── summary_generator.py    # NEW: XML summary creation
│   └── drift_detector.py       # NEW: Semantic shift detection
└── config/
    └── models.py               # NEW: Model definitions, limits
```

### Acceptance Criteria

- [ ] Can switch models mid-conversation
- [ ] Long conversation triggers summarization (user doesn't notice)
- [ ] Waypoint hotkey works (e.g., Ctrl+M)
- [ ] Topic shift triggers chapter boundary
- [ ] Can regenerate last response
- [ ] Intent mode persists across turns

### Git Checkpoint

```bash
git commit -m "feat: Phase 2 complete - multi-model, context management, waypoints"
git push origin main
```

---

## Phase 3: RAG Pipeline

**Goal**: Add document-aware retrieval with hybrid search, parent-document retrieval, and confidence weighting.

### Deliverables

1. **Document attachment UI**:
   - Drag-drop or file picker
   - Visual indicator of indexed documents
2. **Hybrid retrieval**:
   - FAISS dense vectors
   - BM25 keyword search
   - Reciprocal Rank Fusion (RRF) combination
3. **Parent-document retrieval** (return enclosing context)
4. **Confidence-weighted injection** (metadata to system prompt)
5. **Retrieval blacklist** (topic-based exclusion)
6. **Prompt debugger sidebar** (collapsible, shows assembled prompt)

### Key Files to Create/Modify

```
├── ui/
│   ├── sidebar.py              # MODIFY: Add document panel
│   └── inspector.py            # NEW: Prompt debugger
├── storage/
│   ├── __init__.py             # NEW
│   ├── vector_store_client.py  # NEW: FAISS abstraction
│   ├── bm25_client.py          # NEW: Keyword search
│   ├── document_indexer.py     # NEW: Chunking, embedding
│   ├── retrieval_blacklist.py  # NEW: Exclusion rules
│   └── conversation_store.py   # NEW: .jsonl persistence
└── orchestrator/
    └── prompt_builder.py       # MODIFY: Add RAG injection
```

### Acceptance Criteria

- [ ] Can drag PDF/TXT/MD onto window to index
- [ ] Relevant chunks appear in responses
- [ ] Prompt inspector shows RAG context with scores
- [ ] Blacklist prevents specific docs from surfacing
- [ ] Parent sections returned, not fragments
- [ ] Hybrid search finds error codes and proper nouns

### Git Checkpoint

```bash
git commit -m "feat: Phase 3 complete - hybrid RAG with confidence weighting"
git push origin main
```

---

## Phase 4: Polish & Desktop Integration

**Goal**: Full aesthetic pass, keyboard workflow, exit handling, artifacts.

### Deliverables

1. **Full aesthetic implementation**:
   - Geometric sans-serif fonts (Inter or similar)
   - High-contrast dark palette
   - Proper spacing, visual hierarchy
   - Subtle animations (typing indicator, model switch confirmation)
2. **Keyboard navigation**:
   - Global hotkeys (send, toggle RAG, waypoint, snippet insert)
   - Logical tab order
   - Focus mode toggle (hide chrome)
3. **Exit handling**:
   - Confirmation dialog
   - "Summarize and Exit" generates .jsonl archive
   - Optional artifact generation (outline, decision log)
4. **Token budget indicator** (ambient progress bar)
5. **Windows integration**:
   - Custom icon (taskbar, title bar)
   - Proper minimize/restore behavior
   - Remember window position and size

### Key Files to Create/Modify

```
├── ui/
│   ├── main_window.py          # MODIFY: Hotkeys, focus mode
│   ├── dialogs.py              # NEW: Exit confirmation, artifacts
│   └── theme.qss               # NEW: Qt stylesheet
├── summarization/
│   └── artifact_generator.py   # NEW: Outline, decision log
├── assets/
│   └── icon.ico                # NEW: App icon
└── config/
    └── themes.py               # MODIFY: Full palette
```

### Acceptance Criteria

- [ ] App looks "premium" — not default Qt
- [ ] Can operate entirely via keyboard
- [ ] Focus mode hides everything except input + stream
- [ ] Exit saves structured archive
- [ ] Token indicator shows context usage
- [ ] Window state persists between launches

### Git Checkpoint

```bash
git commit -m "feat: Phase 4 complete - polish, UX, desktop integration"
git push origin main
git tag v1.0.0
git push origin v1.0.0
```

---

## Post-v1 Roadmap (Tier 3 Features)

These are validated ideas deferred to avoid scope creep:

| Feature | Complexity | Value |
|---------|------------|-------|
| Ghost Mode / Global Overlay | High | Different UX paradigm |
| Cross-Session Memory Index | Medium | Vector-index .jsonl summaries |
| Local Model Support (Ollama) | Medium | Offline fallback |
| Vision RAG (Images/PDFs) | High | Multimodal retrieval |
| Audio I/O | Medium | Voice interaction |
| Model Comparison Mode | Low | Side-by-side responses |

---

## Development Rhythm

For each phase:

1. **Read CLAUDE.md** before starting any work
2. **Create files in order** — dependencies first
3. **Test incrementally** — run after each major addition
4. **Commit working states** — don't batch large changes
5. **Push before stopping** — always sync to GitHub
6. **Update CLAUDE.md** if architecture evolves
