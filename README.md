# 🤖 Mitra — Iron Man Jarvis-Style AI Database Analyst

[![UI Style](https://img.shields.io/badge/UI%2FUX-Jarvis%20Iron%20Man%20HUD-00d4ff?style=for-the-badge&logo=react)](https://github.com)
[![3D Engine](https://img.shields.io/badge/3D%20Engine-Three.js%20%2F%20R3F-00ffaa?style=for-the-badge&logo=three.js)](https://github.com)
[![Tech Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20React%20%7C%20Groq%20%7C%20Gemini-8c77ff?style=for-the-badge)](https://github.com)

**Mitra** is a local-first, natural language AI Database Analyst featuring a **stunning, futuristic 3D Jarvis-style UI/UX (Iron Man HUD aesthetic)**. Ask questions in plain English or via voice, and watch Mitra generate safe read-only SQL, stream reasoning steps, render dynamic charts, and provide full database exploration.

---

## 🎬 Application Demo & Visuals

### 🔴 Demonstration Video
<!-- Replace demo.mp4 and demo-thumbnail.png with your video/image file names -->
<p align="center">
  <video src="demo.mp4" controls width="100%" poster="demo-thumbnail.png">
    Your browser does not support the video tag.
  </video>
</p>

### 📸 Application Interface Screenshots
<!-- Add your images directly into the project root or folder and update filenames below -->

#### 1. Jarvis 3D HUD Chat Interface & Streaming SQL
![Jarvis 3D HUD Chat Interface](chat-interface.png)
*Featuring 3D particle constellation, rotating energy rings, holographic infinite grid floor, dynamic arc-reactor JarvisOrb, scanline thinking overlays, and streaming SQL execution.*

#### 2. Searchable Database Explorer & Schema Inspector
![Database Explorer](database-explorer.png)
*Interactive schema inspection, foreign key mapping, data type badges, and 50-row preview table.*

#### 3. Real-Time Analytics Dashboard
![Analytics Dashboard](analytics-dashboard.png)
*14 live data-backed Recharts cards with interactive hover effects and metric cards.*

#### 4. Voice Dictation Engine & Waveforms
![Voice Dictation Engine](voice-dictation.png)
*Microphone ripple animation, live waveform visualizer, silence detection, and Groq Whisper proxy transcription.*

---

## 🚀 The Jarvis UI/UX Experience

The entire frontend interface has been built to replicate the **Iron Man / Stark Industries HUD** experience:

- **🌌 3D Neural Constellation & Floor Grid**: Powered by Three.js / React Three Fiber with 600 drifting instanced particles, 3 concentric animated torus energy rings, and an infinite floor grid.
- **🔮 Interactive `JarvisOrb`**: An arc-reactor glowing core in the chat header that accelerates rotation and pulses with energy whenever the AI is reasoning or running queries.
- **💎 Glassmorphism & Neon Cyan Palette**: Dark void theme (`#020408`) overlaid with frosted glass panels (`backdrop-filter: blur(24px)`), electric blue borders, violet accents, and pulse-glowing status indicators.
- **⚡ Scanline & Materialization FX**: Live top-to-bottom scanline animation during bot thinking states, and smooth Framer Motion spring materialization on incoming message cards.
- **🎙️ HUD Audio Visualizer**: Microphone button with red/blue pulsating ripple animations and live audio waveform bars during speech dictation.

---

## 🔥 Key Features

- **🗣️ Natural Language to SQL**: Ask questions in plain language; Mitra translates your intent into safe read-only SQL queries.
- **🛡️ SQLGlot Read-Only Safety**: Strict AST parsing blocks any `DROP`, `DELETE`, `UPDATE`, or state-altering statements.
- **⚡ Real-Time SSE Streaming**: Live status feedback (*Understanding question...*, *Generating SQL...*, *Executing query...*) streamed direct to the chat bubble.
- **📊 Automatic Visualizations**: Generates inline Bar, Line, Pie, and Area charts (Recharts) and ER diagrams (Mermaid.js).
- **🤖 Multi-LLM Failover**: Automatically switches between **Groq** (`llama-3.3-70b`), **Google Gemini** (`gemini-2.5-flash`), and **Anthropic Claude**.
- **🎙️ Voice Dictation (Dual Engine)**: Browser Web Speech API (zero key) or Groq Whisper (`whisper-large-v3-turbo`) with silence detection & auto-punctuation.
- **🔍 Database Explorer**: Search tables and columns, inspect schema data types, and preview up to 50 rows.
- **📈 Analytics Dashboard**: 14 live charts tracking monthly revenue, category sales, customer tiers, low-stock items, and employee metrics.

---

## 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│              Frontend: React + Vite + Three.js / R3F                    │
│   (Jarvis 3D HUD, Arc Reactor Orb, Framer Motion, Recharts, Mermaid)   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ SSE Stream / HTTP
┌────────────────────────────────────▼────────────────────────────────────┐
│                       FastAPI Backend Server                            │
│           (Agent Controller, SQLGlot Safety, Voice Proxy)               │
└─────────┬──────────────────────────┬──────────────────────────┬─────────┘
          │                          │                          │
┌─────────▼──────────┐     ┌─────────▼──────────┐     ┌─────────▼──────────┐
│ SQLGlot Guardrails │     │ SQLite / SQLAlchemy│     │  Multi-LLM Engine  │
│ (Read-Only Safety) │     │ Database Layer     │     │(Groq/Gemini/Claude)│
└────────────────────┘     └────────────────────┘     └────────────────────┘
```

---

## ⚡ Quick Start

### 1. Configure Environment (`.env`)
Copy `.env.example` to `.env` in the project root:
```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
VOICE_TRANSCRIPTION_MODEL=whisper-large-v3-turbo

# Optional:
GEMINI_API_KEY=your_gemini_key
ANTHROPIC_API_KEY=your_anthropic_key
```

For Groq voice dictation, create `frontend/.env`:
```env
VITE_VOICE_TRANSCRIBER=groq
VITE_VOICE_AUTO_SEND=false
VITE_VOICE_PUNCTUATION=true
```

---

### 2. Run the Application

#### 💻 Windows (PowerShell)

**Terminal 1 (Backend):**
```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 (Frontend):**
```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

#### 🐧 Linux / macOS / WSL

**Terminal 1 (Backend):**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` to launch the **Jarvis HUD AI Database Analyst**!

---

## 🧪 Testing & Verification

```bash
# Backend unit tests
cd backend && pytest -q

# Frontend build & type check
cd frontend && npm run build
```

---

## 📜 License & Disclaimer

Mitra is an AI-powered database assistant designed for read-only analytical queries. All generated queries are AST-checked via SQLGlot to prevent unauthorized database modifications.
