# 🤖 Mitra — Iron Man Jarvis-Style AI Database Analyst

[![UI Style](https://img.shields.io/badge/UI%2FUX-Jarvis%20Iron%20Man%20HUD-00d4ff?style=for-the-badge&logo=react)](https://github.com/kishorekumar-2512/Mitra)
[![3D Engine](https://img.shields.io/badge/3D%20Engine-Three.js%20%2F%20R3F-00ffaa?style=for-the-badge&logo=three.js)](https://github.com/kishorekumar-2512/Mitra)
[![Tech Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20React%20%7C%20Groq%20%7C%20Gemini%20%7C%20Claude-8c77ff?style=for-the-badge)](https://github.com/kishorekumar-2512/Mitra)

**Mitra** is a high-performance, local-first natural language AI Database Analyst featuring a **futuristic 3D Jarvis-style UI/UX (Iron Man HUD aesthetic)**. Ask database questions in plain English or via voice, and watch Mitra execute safe read-only SQL, stream reasoning steps via Server-Sent Events (SSE), render dynamic interactive charts, and provide comprehensive database exploration.

---

## 🎬 Application Video Demo & Visual Showcase

### 🔴 Complete Application Demonstration Video
https://github.com/user-attachments/assets/demo-video.mp4

<p align="center">
  <video src="assets/demo-video.mp4" controls width="100%" poster="assets/chat-interface.png">
    Your browser does not support HTML5 video. You can view the video file directly at <a href="assets/demo-video.mp4">assets/demo-video.mp4</a>.
  </video>
</p>

---

### 📸 Application Interface Screenshots

#### 1. 🌌 Jarvis 3D HUD Chat Interface & Live SSE Streaming
![Jarvis 3D HUD Chat Interface](assets/chat-interface.png)
*Features a 3D neural constellation background, rotating energy rings, infinite holographic grid floor, arc-reactor `JarvisOrb`, real-time scanline thinking indicators, and streaming SQL execution.*

---

#### 2. 🎙️ Voice Dictation Engine & Waveforms
![Voice Dictation Engine](assets/voice-dictation.png)
*Microphone input bar with glowing visualizer, keyboard shortcuts (`Enter` send, `Shift` + `Enter` newline), provider settings toggle, and dual-engine voice transcription.*

---

#### 3. 🔍 Searchable Database Explorer & Schema Inspector
![Database Explorer](assets/database-explorer.png)
*Interactive schema inspection, foreign key mapping, column data-type badges, search filtering, and instant 50-row table previews.*

---

#### 4. 📊 Real-Time Analytics Dashboard
![Analytics Dashboard](assets/analytics-dashboard.png)
*Curated library of live data-backed Recharts visual cards (Line, Bar, Pie) with PNG export, CSV download, and interactive pinning.*

---

#### 5. 💬 Sidebar & Conversation History
![Sidebar History](assets/sidebar-history.png)
*Searchable 7-day conversation history, quick workspace status monitors, and one-click thread navigation.*

---

## 🔄 Agent & Pipeline Architecture

```mermaid
flowchart TD
    User([User Question / Voice Input]) --> Frontend[React 18 + R3F Jarvis HUD]
    Frontend -->|POST /api/chat - SSE Stream| Backend[FastAPI Backend Core]
    
    subgraph Agent Loop & Multi-LLM Failover
        Backend --> PreCheck{Conversational / Out-of-Bound?}
        PreCheck -->|Greeting/Scope Check| QuickReply[Instant Conversational Response]
        PreCheck -->|Database Query| ProviderSelect[Select Primary LLM Candidate]
        
        ProviderSelect -->|Attempt 1| Groq[Groq Llama-3.3-70B]
        Groq -->|Rate Limit / 429| Gemini[Gemini 2.5 Flash]
        Gemini -->|Format Error / Key Missing| Claude[Anthropic Claude 4.5]
        Claude -->|All Failed| Offline[Built-In Reviewed Offline Analysis]
        
        Groq -->|Success| ModelOutput[Tool Calls / Response]
        Gemini -->|Success| ModelOutput
        Claude -->|Success| ModelOutput
    end
    
    subgraph Tool Execution & Guardrails
        ModelOutput --> ToolCheck{Tool Requested?}
        ToolCheck -->|get_schema| DB_Schema[Inspect Schema & Foreign Keys]
        ToolCheck -->|execute_query| SQL_Guard[SQLGlot Read-Only Guardrail]
        ToolCheck -->|generate_chart| Chart_Gen[Recharts Specification Generator]
        ToolCheck -->|generate_flowchart| Mermaid_Gen[Mermaid ER & Flowchart Renderer]
        ToolCheck -->|explain_data| Insight_Gen[Grounded Plain-Text Summary]
        
        SQL_Guard -->|Pass SELECT Only| SQLite[(SQLite Database)]
        SQL_Guard -->|Fail Non-SELECT| ErrorReturn[Return Guardrail Violation Error]
    end
    
    SQLite --> ResultTable[Return Query Rows & Columns]
    ResultTable --> Frontend
    Chart_Gen --> Frontend
    Insight_Gen --> Frontend
    QuickReply --> Frontend
```

---

## ⚡ Multi-LLM Failover Engine & API Compatibility

Mitra features an **agentic tool-calling loop** with intelligent failover across multiple state-of-the-art LLM providers:

1. **Groq (`llama-3.3-70b-versatile`)**: Ultra-fast tool-calling inference.
2. **Google Gemini (`gemini-2.5-flash`)**: High-throughput reasoning fallback with custom recursive JSON Schema sanitizer that strips unsupported keywords (`$defs`, `title`, `default`, `anyOf`).
3. **Anthropic Claude (`claude-sonnet-4-5`)**: Precision analytical reasoning.
4. **Deterministic Offline Fallback**: If upstream provider quotas or keys are exhausted, Mitra safely runs built-in read-only analytical queries without inventing or fabricating answers.

---

## 🛡️ SQL Security & Read-Only Guardrails

Safety is built into the parser level:
- **AST Parsing**: Powered by `sqlglot` to parse incoming SQL into Abstract Syntax Trees.
- **Strict Read-Only Enforcement**: Any query containing `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, or multi-statement execution is instantly rejected before reaching the database.
- **Result Row Truncation**: Capped at 500 rows to prevent memory exhaustion and browser freeze.

---

## 🚀 The Jarvis 3D HUD UI/UX Experience

- **🌌 3D Neural Constellation & Floor Grid**: Built with Three.js / React Three Fiber featuring 600 drifting instanced particles, concentric torus energy rings, and an infinite floor grid.
- **🔮 Interactive `JarvisOrb`**: Arc-reactor glowing core in the chat header that accelerates rotation and pulses with energy during agent execution.
- **💎 Glassmorphism & Neon Cyan Palette**: Dark void theme (`#020408`) overlaid with frosted glass panels (`backdrop-filter: blur(24px)`), electric blue borders, and neon cyan accents.
- **🎙️ HUD Audio Visualizer**: Microphone button with pulsating ripple animations and live audio waveform bars during speech dictation.

---

## 💻 Tech Stack

- **Frontend**: React 18, Vite, TypeScript, Three.js, React Three Fiber, Recharts, Mermaid.js, Lucide Icons, Vanilla CSS.
- **Backend**: Python 3.12, FastAPI, SQLAlchemy, SQLGlot, AsyncHTTPX, Pydantic v2.
- **LLM Integrations**: Groq SDK, Anthropic SDK, Gemini REST API, Groq Whisper API.

---

## ⚙️ Setup & Installation

### 1. Environment Configuration (`.env`)
Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

ANTHROPIC_API_KEY=your_anthropic_api_key_here
CLAUDE_MODEL=claude-sonnet-4-5-20250929

DATABASE_URL=sqlite+aiosqlite:///./data/insightforge.db
REDIS_URL=redis://localhost:6379/0
VOICE_TRANSCRIPTION_MODEL=whisper-large-v3-turbo
```

### 2. Running Locally

#### 🐍 Backend (FastAPI)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### ⚛️ Frontend (Vite + React)
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` to launch **Mitra**.

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
