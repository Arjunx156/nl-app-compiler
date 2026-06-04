# NL App Compiler

A production-grade **Natural Language → App Schema Compiler** powered by Google Gemini.

## What It Does

Type a plain-English app description, and the system outputs a complete, validated, execution-ready JSON configuration bundle:

- **UI Schema** — pages, components, layouts, navigation
- **API Schema** — endpoints, methods, request/response shapes
- **DB Schema** — tables, columns, types, relations, indexes
- **Auth Schema** — roles, permissions matrix, protected routes
- **Business Logic** — gating, access control rules

## Architecture

```
User Prompt
    ↓
Stage 1: IntentExtractor       (gemini-2.0-flash)
    ↓
Stage 2: SystemArchitect       (gemini-1.5-pro)
    ↓
Stage 3: Schema Generators ×4  (gemini-1.5-pro, parallel)
  ├── UISchemaGenerator
  ├── APISchemaGenerator
  ├── DBSchemaGenerator
  └── AuthSchemaGenerator
    ↓
Stage 4: CrossLayerValidator   (10 cross-layer checks)
    ↓
Stage 5: RepairEngine          (surgical, max 3 iterations)
    ↓
CompilationResult (full JSON bundle)
```

## Tech Stack

- **Backend**: FastAPI + Python 3.11 + Pydantic v2
- **LLM**: Google Gemini API (gemini-2.0-flash + gemini-1.5-pro)
- **Database**: SQLite (async via aiosqlite + SQLAlchemy)
- **Streaming**: Server-Sent Events
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind CSS
- **UI Components**: shadcn/ui + Framer Motion + Recharts

## Setup

See detailed setup instructions below (added after build completion).

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Your Google Gemini API key |
