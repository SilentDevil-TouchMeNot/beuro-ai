# 🏛️ Beuro AI — Government Service Autopilot

> An Agentic AI assistant that guides Indian citizens step-by-step through government bureaucracy — with voice, multilingual support, and live official links.

---

## 📋 Table of Contents

- [What is Beuro AI?](#what-is-beuro-ai)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Setup & Installation](#setup--installation)
- [How to Run](#how-to-run)
- [Agentic AI Implementation](#agentic-ai-implementation)
- [NLP Components](#nlp-components)
- [Features](#features)
- [API Reference](#api-reference)
- [Rate Limits & Model Rotation](#rate-limits--model-rotation)
- [Supported Services](#supported-services)
- [Supported Languages](#supported-languages)

---

## What is Beuro AI?

Beuro AI is an **Agentic AI** application that acts as a personal bureaucracy navigator for India. Instead of a user having to figure out which portal to visit, what documents to bring, and what steps to follow — Beuro AI handles it all conversationally.

You simply say **"I want a passport"** and the agent:
1. Understands your intent (NLP topic detection)
2. Asks clarifying questions to collect your personal data
3. Returns a numbered step-by-step guide
4. Surfaces the exact official government portals to visit
5. Remembers your data across the session (state management)
6. Speaks the reply aloud in your chosen language (TTS)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        USER (Browser)                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Frontend  (index.html)                   │   │
│  │  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐  │   │
│  │  │  Chat UI │ │  Voice   │ │  Lang  │ │   TTS    │  │   │
│  │  │ Bubbles  │ │ Input🎤  │ │ Detect │ │ Output🔊 │  │   │
│  │  └──────────┘ └──────────┘ └────────┘ └──────────┘  │   │
│  │          ↕  REST API calls (fetch)                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP POST /api/chat
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend  (FastAPI + Uvicorn)               │
│                                                             │
│  ┌──────────┐    ┌─────────────────┐    ┌───────────────┐  │
│  │  router  │───▶│ workflow_engine  │───▶│  llm_client   │  │
│  │  .py     │    │      .py        │    │     .py       │  │
│  │          │    │  • Build prompt  │    │ • Gemini 2.5  │  │
│  │ /chat    │    │  • Parse JSON    │    │ • Gemini 3.5  │  │
│  │ /health  │    │  • Merge state   │    │ • Gemini Lite │  │
│  │ /links   │    │  • Attach links  │    │ • Groq LLAMA  │  │
│  │ /download│    └─────────────────┘    └───────────────┘  │
│  └──────────┘                                               │
│       │               ┌───────────┐    ┌───────────────┐   │
│       └──────────────▶│ storage   │    │ form_downloader│   │
│                        │   .py    │    │     .py       │   │
│                        │ JSON     │    │ PDF fill/     │   │
│                        │ sessions │    │ reportlab     │   │
│                        └──────────┘    └───────────────┘   │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────┐
        │   Google Gemini API     │
        │   (generativelanguage   │
        │    .googleapis.com)     │
        └─────────────────────────┘
```

### Data Flow for a Single Chat Message

```
User types "I want passport"
        │
        ▼
[Frontend] Detects topic = "passport"
        │
        ▼
POST /api/chat  { topic, message, session_id, language }
        │
        ▼
[router.py] Validates payload → loads session data from JSON
        │
        ▼
[workflow_engine.py]
  1. Builds system prompt (with topic, language, collected data so far)
  2. Injects official links for "passport" topic into prompt
  3. Calls ask_llm()
        │
        ▼
[llm_client.py]
  1. Tries gemini-2.5-flash  →  if 429, cools down 65s
  2. Tries gemini-3.5-flash  →  if 429, cools down 65s
  3. Tries gemini-2.5-flash-lite → if 429, returns graceful stub
        │
        ▼
[Gemini API] Returns JSON:
  { "reply": "Step 1: ...", "updated_data": { "Name": "Rahul" } }
        │
        ▼
[workflow_engine.py]
  • Parses JSON reply
  • Merges new fields into session state
  • Attaches 5 official link cards
        │
        ▼
[storage.py] Saves updated session to data/sessions/<session_id>.json
        │
        ▼
Response: { reply, updated_data, steps }
        │
        ▼
[Frontend]
  • Renders reply with numbered steps + bold text
  • Renders clickable official link cards
  • Speaks reply via TTS (split into sentence chunks)
  • Shows language detection banner if non-English detected
```

---

## Project Structure

```
final beuro ai agent/
│
├── .env                        # API keys (GEMINI_API_KEY, GROQ_API_KEY)
├── requirements.txt            # Python dependencies
│
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point + static file serving
│   ├── router.py               # API route definitions (/chat, /health, /links, /download)
│   ├── workflow_engine.py      # Core AI logic: prompting, parsing, state merging
│   ├── llm_client.py           # Multi-model LLM chain with 429 fallback rotation
│   ├── storage.py              # JSON session persistence
│   ├── link_fetcher.py         # DuckDuckGo scraper for .gov.in links
│   ├── form_downloader.py      # PDF form download + filling (pypdf2 / reportlab)
│   └── translator.py           # Multilingual UI string definitions
│
├── frontend/
│   ├── index.html              # Full single-page app (HTML + CSS + JS)
│   └── static/
│       └── style.css           # Supplementary styles
│
├── data/
│   └── sessions/               # Auto-created; one JSON file per session
│       └── <session_id>.json
│
└── venv/                       # Python virtual environment
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Vanilla HTML / CSS / JavaScript | Single-page chat UI — no framework needed |
| **Styling** | Custom CSS with glassmorphism | Dark premium design with backdrop-filter blur |
| **Voice Input** | Web Speech API (`SpeechRecognition`) | Mic-to-text in 11 Indian languages |
| **Voice Output** | Web Speech API (`SpeechSynthesis`) | Text-to-speech with sentence chunking to fix Chrome's 15s cutoff |
| **Backend** | FastAPI + Uvicorn | Async REST API server |
| **LLM Primary** | Google Gemini 2.5 Flash | Main AI model for generating responses |
| **LLM Fallback 1** | Google Gemini 3.5 Flash | Activated when 2.5 Flash hits rate limit |
| **LLM Fallback 2** | Google Gemini 2.5 Flash Lite | Last resort before graceful error stub |
| **LLM Fallback 3** | Groq (LLaMA 3.1 8B) | Optional; activated if `GROQ_API_KEY` is set |
| **Session Storage** | JSON files on disk | Lightweight, no database needed |
| **PDF Handling** | pypdf2 + reportlab | Download and fill government PDF forms |
| **HTTP Client** | httpx (async) | Non-blocking API calls to LLM providers |

---

## Setup & Installation

### Prerequisites

- Python 3.10 or higher
- A free **Google Gemini API key** → [Get one here](https://aistudio.google.com/app/apikey)
- Chrome or Edge browser (for voice features)

### 1. Clone the project

```bash
git clone https://github.com/SilentDevil-TouchMeNot/beuro-ai.git
cd beuro-ai
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# OR
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Add your API key

Open the `.env` file in the project root and paste your key:

```
GEMINI_API_KEY=AIzaSy_YOUR_KEY_HERE
```

> Optionally add `GROQ_API_KEY=sk-...` for an extra fallback LLM.

---

## How to Run

```bash
# From the project root, with venv activated:
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Then open **http://127.0.0.1:8000** in Chrome.

To stop: press **Ctrl + C** in the terminal.

### One-liner

```bash
cd beuro-ai && source venv/bin/activate && uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

---

## Agentic AI Implementation

Beuro AI is an **agentic** system — not just a chatbot. Here is what makes it agentic:

### 1. Goal-Directed Behaviour
The agent has a clear goal per session: **guide the user to completion of a specific government service**. Every response is shaped around making progress toward that goal — not just answering the latest message in isolation.

### 2. State Management (Memory)
The agent maintains **persistent session state** across the entire conversation. Every piece of information the user reveals (name, date of birth, Aadhaar number, address, etc.) is extracted from their message and stored in a JSON file keyed to their `session_id`. On the next message, this accumulated data is injected back into the system prompt so the LLM "remembers" everything the user has said.

```python
# workflow_engine.py
current_data = load_session(session_id)          # Load memory
reply, updated_data, steps = process_user_message(...)
save_session(session_id, updated_data)           # Write back memory
```

### 3. Tool Use (Link & Form Actions)
The agent doesn't just talk — it:
- **Fetches official government links** curated per topic
- **Downloads and fills PDF forms** using user data collected during the conversation
- **Surfaces real portal URLs** (passportindia.gov.in, uidai.gov.in, etc.)

### 4. Multi-Step Planning
The system prompt instructs the LLM to produce **numbered step-by-step plans** — not single-turn answers. The agent reasons about the full process (e.g., register → upload docs → book appointment → attend PSK) and walks the user through it sequentially.

### 5. Adaptive Clarification
After every response, the agent identifies the **single most important missing piece of information** and asks for it explicitly. This mimics how a human expert would guide a client — collecting data progressively.

### 6. Autonomous Provider Failover
The LLM client acts as an **autonomous decision-maker** for choosing which AI provider to use. Without any human intervention, it:
- Detects a 429 rate-limit response
- Puts that model on a 65-second cooldown
- Switches to the next available provider
- Returns a graceful message if all providers are exhausted

This is a form of **self-healing agentic behaviour**.

---

## NLP Components

### 1. Intent Detection (Rule-Based NER)

**File:** `frontend/index.html` → `currentTopic(text)`

Before sending a message to the LLM, the frontend performs lightweight keyword-based **Named Entity Recognition** to classify the user's intent into a topic:

```javascript
function currentTopic(text) {
  const t = text.toLowerCase();
  if (t.includes('passport'))                      return 'passport';
  if (t.includes('aadhaar') || t.includes('aadhar')) return 'aadhaar';
  if (t.includes('birth'))                         return 'birth_certificate';
  if (t.includes('pan'))                           return 'pan_card';
  if (t.includes('driving') || t.includes('licence')) return 'driving_licence';
  // ... etc
  return 'general';
}
```

This topic label is sent to the backend and used to:
- Select the correct official links
- Prime the system prompt with domain-specific guidance
- Route PDF form downloads to the right template

### 2. Language Detection (Unicode Script Identification)

**File:** `frontend/index.html` → `detectLanguage(text)` / `LANG_RANGES`

The frontend identifies the **script/language** of user input by matching Unicode block ranges — a classic NLP technique:

```javascript
const LANG_RANGES = [
  { code:'hi', name:'Hindi',    re: /[\u0900-\u097F]/ },  // Devanagari
  { code:'ta', name:'Tamil',    re: /[\u0B80-\u0BFF]/ },  // Tamil script
  { code:'te', name:'Telugu',   re: /[\u0C00-\u0C7F]/ },  // Telugu script
  { code:'bn', name:'Bengali',  re: /[\u0980-\u09FF]/ },  // Bengali script
  { code:'ur', name:'Urdu',     re: /[\u0600-\u06FF]/ },  // Arabic script
  // ... 11 languages total
];
```

When a non-English script is detected, a banner appears offering to switch the response language — the detected language code is then passed to the backend and injected into the LLM system prompt.

### 3. Information Extraction (LLM-based Slot Filling)

**File:** `backend/workflow_engine.py`

This is the core NLP task. The system prompt instructs the LLM to perform **slot filling** — extracting structured data from free-form natural language:

```
System Prompt instructs LLM to output:
{
  "reply": "conversational response",
  "updated_data": {
    "Full Name": "value if user mentioned it",
    "Date of Birth": "value if user mentioned it",
    "Aadhaar Number": "value if user mentioned it"
  }
}
```

The user might write *"My name is Rahul Sharma and I was born on 12th March 1995"* — the LLM extracts `{ "Full Name": "Rahul Sharma", "Date of Birth": "12-03-1995" }` automatically. This is **neural slot-filling** / **information extraction** using the LLM as the NLP engine.

### 4. Multilingual Generation

**File:** `backend/workflow_engine.py` → `process_user_message()`

The system prompt explicitly instructs the LLM to respond in the detected language:

```python
system_prompt = f"""
IMPORTANT: Always reply in {lang_name}.
If the user writes in another language, still reply in {lang_name}.
"""
```

This enables **cross-lingual understanding** — the user can write in Hindi, the LLM understands it (trained multilingually), and responds back in Hindi with proper grammar and fluency.

### 5. Response Structuring (Prompt Engineering as NLP)

**File:** `backend/workflow_engine.py`

The system prompt enforces **structured output** — a prompt engineering technique that constrains the LLM's free-form generation into a deterministic JSON schema. This is essential for reliable downstream parsing:

```python
"""Respond ONLY with a valid JSON object in this exact shape:
{
  "reply": "...",
  "updated_data": { "FieldName": "value" }
}"""
```

Without this, LLMs produce verbose, unpredictable prose. With it, every response is a machine-readable JSON object that the backend can parse, merge into state, and return to the frontend reliably.

### 6. Text-to-Speech Pre-processing (Text Normalisation)

**File:** `frontend/index.html` → `speak(text)`

Before feeding text to the Web Speech API, the system applies NLP **text normalisation**:
- Strips markdown symbols (`**`, `*`, `#`, etc.)
- Removes URLs (they sound terrible when read aloud)
- Segments text into sentence chunks (`/[^.!?\n]{1,200}[.!?\n]?/g`) — using punctuation-based sentence boundary detection

This ensures the TTS engine receives clean, natural prose rather than code-like text.

---

## Features

| Feature | Description |
|---|---|
| 🎤 **Voice Input** | Speak your query in any of 11 Indian languages |
| 🔊 **Voice Output** | Full TTS readback — entire reply, not just first sentence |
| 🌐 **11 Languages** | English, Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Urdu |
| 🔍 **Auto Language Detect** | Detects script from Unicode range and offers to switch |
| 🤖 **Agentic Memory** | Remembers everything you said across the conversation |
| 📋 **Step-by-Step Guide** | Numbered steps with numbered visual pills in UI |
| 🔗 **Official Link Cards** | Clickable cards with real government portal URLs |
| 🔄 **Model Rotation** | Auto-switches between 3 Gemini models on rate limit |
| 💬 **Quick Chips** | One-tap shortcuts for 6 common services |
| 🗑️ **Clear Chat** | Resets session and memory |
| 📄 **PDF Form Filling** | Downloads and fills official government forms |
| ✨ **Glassmorphism UI** | Premium dark UI with animated background orbs |

---

## API Reference

### `POST /api/chat`

Main conversation endpoint.

**Request body:**
```json
{
  "topic": "passport",
  "message": "I want to apply for a passport",
  "session_id": "uuid-string",
  "language": "en"
}
```

**Response:**
```json
{
  "reply": "Step 1: Register on Passport Seva Portal...",
  "updated_data": { "Full Name": "Rahul Sharma" },
  "steps": [
    { "title": "Passport Seva Portal", "url": "https://passportindia.gov.in" },
    ...
  ]
}
```

### `GET /api/health`

Returns the currently active LLM provider.

```json
{ "active_provider": "Gemini ✅ (active: gemini-2.5-flash)" }
```

---

## Rate Limits & Model Rotation

The system automatically rotates between models when rate limits are hit:

| Priority | Model | Your RPM | Behaviour |
|---|---|---|---|
| 1st | `gemini-2.5-flash` | 5/min | Default — best quality |
| 2nd | `gemini-3.5-flash` | 1/min | Fallback after 429 |
| 3rd | `gemini-2.5-flash-lite` | 1/min | Last resort |
| 4th | Groq LLaMA 3.1 | Unlimited (free) | If `GROQ_API_KEY` is set |

Each model gets a **65-second cooldown** after a 429 response. No manual action is needed.

---

## Supported Services

| Service | Topic Key | Official Portal |
|---|---|---|
| 🛂 Passport | `passport` | passportindia.gov.in |
| 🪪 Aadhaar Update | `aadhaar` | uidai.gov.in |
| 📄 Birth Certificate | `birth_certificate` | crsorgi.gov.in |
| 💳 PAN Card | `pan_card` | tin.tin.nsdl.com |
| 🚗 Driving Licence | `driving_licence` | sarathi.parivahan.gov.in |
| 🚘 Vehicle RC | `vehicle_rc` | vahan.parivahan.gov.in |
| 🗳️ Voter ID | `voter_id` | voters.eci.gov.in |
| 🍚 Ration Card | `ration_card` | nfsa.gov.in |
| 👮 Police Complaint | `police_complaint` | cybercrime.gov.in |

---

## Supported Languages

| Code | Language | Script |
|---|---|---|
| `en` | English | Latin |
| `hi` | Hindi | Devanagari |
| `ta` | Tamil | Tamil |
| `te` | Telugu | Telugu |
| `bn` | Bengali | Bengali |
| `mr` | Marathi | Devanagari |
| `gu` | Gujarati | Gujarati |
| `kn` | Kannada | Kannada |
| `ml` | Malayalam | Malayalam |
| `pa` | Punjabi | Gurmukhi |
| `ur` | Urdu | Arabic (Nastaliq) |

---

## Known Limitations

- Voice input requires **Chrome or Edge** (Firefox does not support `SpeechRecognition`)
- Rate limits on the free Gemini tier mean you may need to wait ~1 minute between bursts of messages
- PDF form filling works best with fillable PDFs; non-fillable ones get a text overlay via reportlab
- Language auto-detection is heuristic (Unicode ranges) — mixed-script text may not detect correctly

---

*Built with ❤️ for Indian citizens navigating government services.*
