# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

**Development server:**
```bash
# Quick start (recommended)
chmod +x run.sh
./run.sh

# Manual start
cd backend
uv run uvicorn app:app --reload --port 8000
```

**Dependencies:**
```bash
uv sync  # Install all dependencies from pyproject.toml
```

**Environment setup:**
Create `.env` file in root with:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**Access points:**
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Architecture Overview

This is a **RAG (Retrieval-Augmented Generation) system** for course materials with the following architecture:

### Core Components

**RAG System (`rag_system.py`)** - Main orchestrator that coordinates all components
**Document Processor (`document_processor.py`)** - Parses structured course documents and creates semantic chunks
**Vector Store (`vector_store.py`)** - ChromaDB integration for semantic search with embeddings
**AI Generator (`ai_generator.py`)** - Anthropic Claude API integration with tool-calling capabilities
**Search Tools (`search_tools.py`)** - Course search tool that Claude can invoke for content retrieval

### Data Flow Architecture

1. **Document Processing Pipeline:**
   - Structured parsing: `Course Title:`, `Course Link:`, `Course Instructor:`, `Lesson N:`
   - Sentence-based chunking with configurable overlap (800 chars, 100 overlap)
   - Context enhancement: adds course/lesson metadata to chunks
   - Vector embedding using sentence-transformers (all-MiniLM-L6-v2)

2. **Query Processing Pipeline:**
   - Frontend → FastAPI → RAG orchestrator → Claude AI (with tools) → Vector search → Response synthesis
   - Session management for conversation context
   - Tool-driven: Claude decides when to search based on query type

3. **Storage Architecture:**
   - ChromaDB collections for vector storage
   - Session management with conversation history
   - Course metadata and content chunks stored separately

### Key Configuration

**Models & API:**
- Anthropic Model: `claude-sonnet-4-20250514`
- Embedding Model: `all-MiniLM-L6-v2`
- Temperature: 0 (deterministic responses)
- Max tokens: 800

**Processing Settings:**
- Chunk size: 800 characters
- Chunk overlap: 100 characters
- Max search results: 5
- Max conversation history: 2 messages

### Document Structure Expected

Course documents in `docs/` folder should follow this format:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [name]

Lesson 0: [lesson title]
Lesson Link: [lesson url]
[lesson content...]

Lesson 1: [next lesson title]
[content continues...]
```

### Important Implementation Details

**Tool-Based Search:** The AI uses a `search_course_content` tool rather than always searching - it decides when search is needed based on query context.

**Context Preservation:** Course and lesson structure is preserved in chunks with prefixes like "Course [title] Lesson [N] content: [chunk]"

**Session Management:** Maintains conversation context across queries with session IDs.

**Smart Chunking:** Uses regex-based sentence splitting that handles abbreviations and maintains semantic boundaries.

### Frontend Integration

- Vanilla HTML/CSS/JS frontend served as static files
- Markdown rendering for AI responses using marked.js
- Collapsible sources display with course chunk references
- Asynchronous query handling with loading states
- always use uv to run the server do not use pip directory
- use uv to run Python files

## Code Quality Tools

**Development dependencies:**
```bash
uv sync --group dev  # Install development dependencies (Black, flake8, isort, mypy)
```

**Code formatting:**
```bash
# Format all Python files with Black
uv run black backend/ main.py

# Sort imports with isort
uv run isort backend/ main.py

# Run complete formatting pipeline
./scripts/format.sh
```

**Code linting and type checking:**
```bash
# Run flake8 linting
uv run flake8 backend/ main.py

# Run mypy type checking
uv run mypy backend/ main.py

# Run complete linting pipeline
./scripts/lint.sh
```

**Complete quality pipeline:**
```bash
# Run formatting, linting, and tests
./scripts/quality.sh
```

**Quality tool configuration:**
- **Black:** Line length 88, Python 3.13 target
- **isort:** Black-compatible profile, line length 88
- **mypy:** Strict type checking with third-party ignores for chromadb and sentence-transformers
- **flake8:** Compatible with Black formatting