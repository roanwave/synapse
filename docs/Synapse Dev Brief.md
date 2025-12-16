# Dev Brief: Single-User Desktop LLM Chat Application (RAG-Optimized)

## Purpose

Build a single-user Windows desktop application that provides a
seamless, flow-state-preserving LLM chat experience with multi-model
support, invisible context management, and optional document-aware RAG.

## Core Design Principles

1.  Flow State Preservation
2.  Strict Separation of Concerns
3.  RAG Correctness
4.  Low Overhead, High Inspectability

## Technology Stack

-   Python 3.11+
-   PySide6
-   FAISS or Chroma
-   Anthropic, OpenAI, OpenRouter APIs

## Architecture Overview

UI / Orchestrator / Storage & Retrieval / LLM Execution

## Module Structure

Detailed breakdown of ui/, orchestrator/, storage/, summarization/, llm/

## Prompt Assembly Contract

Deterministic system + summary + RAG + conversation layout

## Context Lifecycle

Normal flow and drift-triggered summarization behavior

## Document Attachment Behavior

Documents indexed once; retrieved via vector store only

## Exit Behavior

Summarize-and-exit or clean exit

## Non-Goals

No multi-user, no SaaS, no agents

## Development Phases

Phase 1 through Phase 4

## Success Criteria

Undetectable resets, modular RAG, inspectable prompts
