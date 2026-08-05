# AGENT.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bo-Distiller (Cerith) is an intelligent content distillation tool that transforms bookmarked articles into structured knowledge documents. It supports multiple content sources (Cubox, local Markdown, RSS, etc.) and uses two-stage LLM processing to synthesize knowledge.

## Development Commands

### Starting the Development Environment

```bash
# Start both frontend and backend
./dev.sh start

# Stop services
./dev.sh stop

# Restart services
./dev.sh restart

# Check service status
./dev.sh status
```

Services run on:
- Backend: http://127.0.0.1:8000 (API docs at /docs)
- Frontend: http://localhost:5173

### Backend Development

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend directly (if not using dev.sh)
python -m uvicorn src.web.app:app --reload --host 127.0.0.1 --port 8000

# Run CLI commands
python distill.py --help
python distill.py run --limit 10
python distill.py sources add --cubox
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Type checking
npm run type-check
```

## Architecture Overview

### Backend Architecture

The backend follows a modular architecture with clear separation of concerns:

**Core Modules** (`src/`):
- `config.py` - Configuration management with Pydantic models, supports both YAML and database storage
- `storage.py` - SQLite storage layer with WAL mode, manages articles, sync state, topics, and LLM metadata
- `llm_client.py` - OpenAI-compatible LLM client with context window management and token counting
- `llm_metadata.py` - LLM provider metadata manager, fetches from models.dev API with 30-day caching
- `synthesizer.py` - Two-stage content synthesis (batch extraction → knowledge synthesis)
- `cache.py` - Disk-based caching for LLM responses
- `models.py` - Pydantic data models (Article, SourceInfo, etc.)
- `orchestrator.py` - Main orchestration logic for distillation pipeline

**Adapters** (`src/adapters/`):
- Abstract base class pattern for content sources
- `cubox_adapter.py` - Cubox API integration
- `local_markdown.py` - Local file system adapter
- `aggregator.py` - Multi-source aggregation

**Processors** (`src/processors/`):
- `classifier.py` - Keyword-based classification
- `smart_classifier.py` - ML-based clustering (scikit-learn + sentence-transformers)
- `cleaner.py` - Content cleaning and deduplication

**Services** (`src/services/`):
- `sync_service.py` - Background sync orchestration
- `scheduler_service.py` - APScheduler integration for periodic tasks

**Web API** (`src/web/`):
- `app.py` - FastAPI application setup with CORS
- `routers/` - API route modules:
  - `config.py` - Configuration CRUD
  - `articles.py` - Article management
  - `sources.py` - Source management
  - `distill.py` - Distillation tasks
  - `llm.py` - LLM metadata and connectivity testing
  - `topics.py` - Topic management

### Frontend Architecture

React + TypeScript + Vite stack with Ant Design:

**Key Patterns**:
- React Query for server state management (see `hooks/` directory)
- Custom hooks abstract API calls (`useConfig`, `useLLMMetadata`, etc.)
- Component-based architecture with clear separation:
  - `pages/` - Route-level components
  - `components/` - Reusable UI components
  - `api/` - API client functions
  - `hooks/` - Custom React hooks
  - `utils/` - Utility functions and constants

**Important Frontend Features**:
- Dynamic LLM provider configuration with metadata auto-fill from models.dev
- Provider connectivity testing before saving configuration
- Model selection UI with enable/disable toggles
- Only validates the selected provider on save (not all providers)

### Data Flow

1. **Content Ingestion**: Adapters fetch from sources → Storage layer persists to SQLite
2. **Classification**: Processors analyze and categorize articles
3. **Distillation**: Synthesizer performs two-stage LLM processing (batch extraction → synthesis)
4. **Caching**: LLM responses cached to disk to avoid redundant API calls
5. **Web UI**: FastAPI serves both REST API and static frontend build

### Configuration

Configuration is dual-storage:
- YAML file (`config.yaml`) - Legacy support
- SQLite database (`data/distiller.db`) - Primary storage for runtime config

LLM provider metadata is cached in the database (30-day TTL) and sourced from https://models.dev API.

## Important Implementation Details

### LLM Provider Configuration

The system supports multiple LLM providers (DeepSeek, Xiaomi, Moonshot, Kimi, etc.) with automatic metadata fetching:

- Provider metadata (base URL, context limits) auto-populated from models.dev
- Custom provider option allows manual configuration
- Connectivity testing validates API key + base URL + model before saving
- Only the selected default provider is validated on save
- Call mode is always "direct" (Agent CLI option removed)

### Storage Layer

- Uses SQLite with WAL mode for concurrent access
- Three main tables: `articles`, `sync_state`, `topics`, plus config/metadata tables
- Articles have deduplicated URLs and track source metadata
- LLM metadata cached with timestamps for 30-day refresh cycle

### Context Window Management

The synthesizer automatically handles context window limits:
- Calculates token counts using tiktoken
- Applies safety margins to avoid truncation
- Truncates article content if needed to fit within limits

### Frontend State Management

- React Query handles all server state with automatic caching and revalidation
- Form state managed by Ant Design Form components
- Provider selection state determines which configuration card to display
- Connectivity test results stored in component state (not persisted)

## Key Files to Understand

- `src/web/app.py` - FastAPI application entry point
- `src/storage.py` - Database schema and operations
- `src/config.py` - Configuration models and validation
- `src/llm_metadata.py` - Provider metadata management
- `frontend/src/pages/settings/LLMSettings.tsx` - Main settings UI
- `frontend/src/components/ProviderConfigCard.tsx` - Provider config with connectivity testing

## Environment Setup

Required environment variables (in `.env`):
- LLM provider API keys (e.g., `DEEPSEEK_API_KEY`, `MINIMAX_API_KEY`)
- Cubox token (if using Cubox adapter)

Configuration file `config.yaml` or database `data/distiller.db` must exist (use `config.example.yaml` as template).
