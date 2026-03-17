# Universal Web Scraper AI

AI-powered web scraper with a Streamlit UI that uses Google Gemini to intelligently extract structured data from any website.

## Extraction Logs

[Logs of extracted data](https://drive.google.com/drive/folders/1Gl2aB0rZbtGIm5A1KX-yRBsdbtnf0Sxy?usp=drive_link)

## Features

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

- Python 3.10+
- Google Gemini API key (**required**)
- ScraperAPI key 

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
SCRAPERAPI_KEY=your_scraperapi_key_here   # you can get free for 1 week -you can test without it rarely it reaches here
```

## Usage

```bash
streamlit run app.py
```

The sidebar offers three modes:

| Mode | Description |
|------|-------------|
| **Standard** | Provide a URL and a description of the data you want — the pipeline handles the rest. |
| **Auto-detect** | AI scans the page and suggests data types it found; pick one to extract. |
| **Two-phase** | Crawl first, review/edit the inferred schema, then run extraction with your adjustments. |

## Project Structure

```
web_scrapper/
├── app.py                  # Streamlit entry point
├── config.py               # Central configuration & env loading
├── models.py               # Pydantic data models
├── agents/                 # CrewAI agent orchestration
│   ├── crew.py             # Main pipeline runner
│   ├── direct_mode.py      # Direct (non-agent) execution path
│   └── tools.py            # Agent tool definitions
├── crawler/                # 4-layer crawling engine
│   ├── engine.py           # Layer orchestrator
│   ├── layer1_stealth.py   # Stealth browser crawl
│   ├── layer2_undetected.py# Undetected Chrome
│   ├── layer3_proxy.py     # ScraperAPI proxy
│   ├── layer4_jina.py      # Jina reader fallback
│   ├── classifier.py       # Page content classifier
│   └── validator.py        # HTML validation
├── extraction/             # AI extraction pipeline
│   ├── extractor.py        # Chunked parallel extraction
│   ├── auto_detect.py      # Auto-detect data types
│   ├── schema_builder.py   # Dynamic Pydantic schema generation
│   ├── confidence.py       # Extraction confidence scoring
│   └── prompt_refiner.py   # Prompt refinement
├── pagination/             # Pagination handling
│   ├── heuristic.py        # Rule-based pagination detection
│   ├── ai_fallback.py      # AI-based pagination detection
│   └── rate_limiter.py     # Request rate limiting
├── ui/                     # Streamlit UI components
│   ├── sidebar.py          # Sidebar controls
│   ├── results_table.py    # Results display
│   ├── chat_panel.py       # Chat with data
│   ├── export.py           # CSV/JSON export
│   ├── quality_dashboard.py# Data quality stats
│   ├── schema_editor.py    # Schema editing UI
│   ├── insights_tab.py     # Data insights
│   ├── transparency_panel.py# Pipeline transparency
│   └── progress_feed.py    # Real-time progress
├── utils/                  # Shared utilities
│   ├── cache.py            # Response caching
│   ├── fingerprint.py      # Browser fingerprint helpers
│   └── logger.py           # Logging setup
├── requirements.txt
├── .env.example            # Environment variable template
├── ARCHITECTURE.pdf        # Detailed architecture documentation
├── PROJECT_DOCUMENTATION.pdf # Complete project documentation
```

## How It Works

```
Sidebar input → Crawler (4 layers) → Schema inference → Extraction (chunked, parallel) → Validation → Results + Export + Chat
```

1. **Crawl** — The engine tries each crawler layer in order until it gets valid HTML.
2. **Schema** — Gemini infers a Pydantic schema from the page content (or uses your description).
3. **Extract** — HTML is chunked and processed in parallel; Instructor enforces the schema.
4. **Validate** — Results are scored for completeness and duplicates.
5. **Present** — Data appears in a table with export, chat, quality, and insight panels.

## Documentation

- **ARCHITECTURE.pdf** — Component-by-component architecture breakdown with data flow diagrams
- **PROJECT_DOCUMENTATION.pdf** — Full project guide covering setup, usage, internals, and design decisions

## License
MIT License
