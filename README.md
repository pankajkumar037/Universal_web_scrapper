# Universal Web Scraper AI

AI-powered web scraper with a Streamlit UI that uses Google Gemini to intelligently extract structured data from any website.


## Extraction Logs

[Logs of extracted data](https://drive.google.com/drive/folders/1Gl2aB0rZbtGIm5A1KX-yRBsdbtnf0Sxy?usp=drive_link)
=======
## Logs of extracted data
(https://drive.google.com/drive/folders/1Gl2aB0rZbtGIm5A1KX-yRBsdbtnf0Sxy?usp=drive_link)



## Features

- **Smart Mode** — just describe what to scrape in plain English; AI resolves the URL for you
- **4-layer intelligent crawler** — stealth browse → undetected Chrome → ScraperAPI proxy → Jina reader fallback
- **AI-powered extraction** via Google Gemini + Instructor for structured output
- **Auto-detect mode** — AI automatically discovers data types present on the page
- **Two-phase mode** — crawl first, edit the inferred schema, then extract
- **Pagination detection** — heuristic rules with AI fallback
- **Real-time progress feed** in the UI
- **Quality dashboard** — empty/duplicate field statistics
- **Export to CSV / JSON**
- **Chat with extracted data** — ask questions about results using Gemini Q&A
- **Data insights & transparency panel**

## Prerequisites

- Python 3.11+
- Google Gemini API key (**required**)
- ScraperAPI key (optional — needed only for heavily bot-protected sites)
- Tavily API key (optional — needed for Smart Mode on unknown sites)

## Installation

```bash
git clone https://github.com/pankajkumar037/Universal_web_scrapper.git
cd Universal_web_scrapper
pip install -r requirements.txt
playwright install
```

## Configuration

Create a `.env` file in the project root (see `.env.example` for reference):

```
GEMINI_API_KEY=your_gemini_api_key_here
SCRAPERAPI_KEY=your_scraperapi_key_here   # optional — free trial available
TAVILY_API_KEY=your_tavily_api_key_here   # optional — only needed for Smart Mode on unknown sites
```

## Usage

```bash
streamlit run app.py
```

The sidebar offers three modes:

| Mode | Description |
|------|-------------|
| **Smart Mode** | No URL needed. Describe what you want in plain English (e.g. *"python jobs on LinkedIn in India"*) — AI resolves the URL and runs the scraper. |
| **Two-phase** | Provide a URL + description. Crawl first, review/edit the inferred schema, then extract. |
| **Auto-detect** | Provide a URL only. AI scans the page and suggests data types it found; pick one to extract. |

## Project Structure

```
web_scrapper/
├── app.py                  # Streamlit entry point
├── config.py               # Central configuration & env loading
├── models.py               # Pydantic data models
├── agents/
│   └── crew.py             # Orchestration pipeline + ValidateTool
├── crawler/                # 4-layer crawling engine
│   ├── engine.py           # Layer orchestrator
│   ├── layer1_stealth.py   # crawl4ai magic mode
│   ├── layer2_undetected.py# crawl4ai stealth + simulate_user
│   ├── layer3_proxy.py     # ScraperAPI proxy (JS render)
│   ├── layer4_jina.py      # Jina reader fallback (free)
│   └── validator.py        # Word count / block phrase / density checks
├── extraction/
│   ├── extractor.py        # Batch & chunked parallel extraction
│   ├── auto_detect.py      # Auto-detect data types (CrewAI + Gemini)
│   ├── intent_agent.py     # Smart Mode: conversational URL resolver
│   ├── schema_builder.py   # Dynamic Pydantic model factory
│   └── prompt_refiner.py   # Schema inference from user description
├── pagination/
│   ├── heuristic.py        # Regex-based pagination detection
│   ├── ai_fallback.py      # Gemini-based pagination detection
│   └── rate_limiter.py     # Request rate limiting
├── ui/
│   ├── sidebar.py          # Mode toggles, Smart Mode chat, URL input
│   ├── results_table.py    # Results display
│   ├── chat_panel.py       # Chat with extracted data
│   ├── export.py           # CSV/JSON export
│   ├── quality_dashboard.py# Field completeness & duplicate stats
│   ├── schema_editor.py    # Schema editing UI
│   ├── insights_tab.py     # AI-generated data insights
│   ├── transparency_panel.py# Telemetry display
│   └── progress_feed.py    # Real-time pipeline progress
├── utils/
│   ├── fingerprint.py      # Fuzzy content hash for duplicate page detection
│   └── logger.py           # Logging setup
├── requirements.txt
├── .env.example            # Environment variable template
├── ARCHITECTURE.pdf        # Detailed architecture documentation
└── PROJECT_DOCUMENTATION.pdf # Complete project documentation
```

## How It Works

```
Sidebar input → Crawler (4 layers) → Schema inference → Schema editor → Extraction (batch / chunked parallel) → Validation → Dedup → Results + Export + Chat
```

1. **Crawl** — Tries each of 4 crawler layers until content passes word count, block-phrase, and density checks.
2. **Plan** — Gemini infers a typed schema from your description + a sample of the page. Pagination URLs detected in parallel.
3. **Schema editor** — Review and adjust the inferred fields before extraction starts.
4. **Extract** — Content ≤100k chars: single Gemini call. Larger: split into 100k-char chunks with 2k overlap, 3 parallel workers.
5. **Validate** — Quality report: empty fields per column, exact duplicate count. Records not modified.
6. **Present** — Table, quality dashboard, export (CSV/JSON), chat, and insights panels.

## Documentation

- **ARCHITECTURE.pdf** — Component-by-component architecture breakdown with data flow diagrams
- **PROJECT_DOCUMENTATION.pdf** — Full project guide covering setup, usage, internals, and design decisions

## License
MIT License
