# 🚀 Natural Language to App Compiler

A production-grade **Natural Language → App Schema Compiler** powered by Google Gemini. Type a plain-English app description, and the system outputs a complete, validated, execution-ready JSON configuration bundle.

## ✨ What It Does

Provide an intent (e.g., *"Build a CRM with login, contacts, dashboard, and role-based access for sales and admins."*) and the compiler generates:

1. **UI Schema**: Pages, components, layouts, navigation, and API data bindings.
2. **API Schema**: REST endpoints, HTTP methods, request/response bodies, and authentication requirements.
3. **DB Schema**: Tables, columns, foreign keys, relationships, and indexes.
4. **Auth Schema**: Role definitions, permissions matrix, and protected routes.

## 🏗️ Architecture

The system uses a **multi-stage LLM pipeline** with a surgical repair engine:

```text
User Prompt
    ↓
[Stage 1: IntentExtractor]      (gemini-2.0-flash)
    ↓
[Stage 2: SystemArchitect]      (gemini-1.5-pro)
    ↓
[Stage 3: SchemaGenerators]     (Parallel: UI, API, DB, Auth via gemini-1.5-pro)
    ↓
[Stage 4: CrossLayerValidator]  (10 deterministic checks)
    ↓
[Stage 5: RepairEngine]         (Targeted regeneration loop, max 3 retries)
    ↓
[CompilationResult JSON]        (Saved to SQLite + Streamed via SSE)
```

## 🛡️ Validation System

The **CrossLayerValidator** enforces absolute consistency across schemas:
1. API endpoints reference valid DB tables.
2. API request/response fields match DB table columns.
3. UI components bind to existing API endpoints.
4. UI forms map perfectly to API request bodies.
5. Protected UI routes exist in the auth configuration.
6. Roles assigned to APIs exist in the Auth Schema.
7. Foreign keys point to valid tables/columns.
8. No circular dependencies in data flow.
9. Required API fields correspond to non-nullable DB columns.
10. Monetization/Role gating references valid entities.

If a validation check fails, the **RepairEngine** surgically isolates the broken component, feeds the exact error back to the responsible LLM generator, and patches the schema without restarting the entire pipeline.

## 🛠️ Tech Stack

**Frontend**
- **Next.js 14 (App Router)**
- **Tailwind CSS + Framer Motion**: Glassmorphism aesthetic with animated real-time pipeline status tracking.
- **Lucide Icons & React Syntax Highlighter**: Beautiful visual representations of outputs.

**Backend**
- **FastAPI (Python 3.11+)**: Async IO and high-performance routing.
- **Pydantic v2**: Strict schema definition and LLM output parsing.
- **Google Gemini API**: Utilizing `gemini-2.0-flash` for fast intent extraction and `gemini-1.5-pro` for complex schema architecting.
- **SQLAlchemy (async) + SQLite**: Local persistence of generation history and evaluation metrics.
- **Server-Sent Events (SSE)**: Streaming execution progress to the frontend.

## 🚀 Setup & Installation

### Prerequisites
- Python 3.11+
- Node.js 20+
- Google Gemini API Key

### Backend Setup
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate # Mac/Linux

pip install -r requirements.txt

# Create .env and add your key
echo "GEMINI_API_KEY=your_key_here" > .env

# Run server
uvicorn main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start Next.js dev server
npm run dev
```
Navigate to `http://localhost:3000`

### Docker Compose
```bash
docker-compose up --build
```

## 📊 Evaluation & Metrics
The backend features an automated evaluation engine (`/api/eval/run-all`) loaded with 20 distinct test cases (10 normal apps, 10 edge cases). 

**Metrics Tracked:**
- Validation Score (0-100%)
- Repair Iterations needed
- Total Latency (ms)
- Token Usage
- Cost per generation ($)

## 💡 Tradeoffs & Decisions
1. **Google Gemini Native JSON**: We force `application/json` natively at the API level with Pydantic JSON schemas. This is drastically more reliable than zero-shot JSON prompting.
2. **Multi-Stage vs Single-Shot**: Generating the entire app bundle in one prompt leads to context window collapse and massive hallucination. Breaking it into Intent → Architect → Parallel Schemas ensures high quality and allows surgical repairs.
3. **Surgical Repair**: When an error occurs (e.g., API references a missing DB table), we don't regenerate the whole DB. The RepairEngine only regenerates the missing table and injects it back, saving tokens, time, and preventing cascading failures.
