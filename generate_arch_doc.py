"""Generate a detailed, colorful architectural PDF for the Universal Scraper AI project."""

import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether, ListFlowable, ListItem,
)
from reportlab.lib.colors import HexColor

# ── Color Palette ──────────────────────────────────────────────────
DARK_BG       = HexColor("#1a1a2e")
PRIMARY       = HexColor("#0f3460")
ACCENT        = HexColor("#e94560")
ACCENT2       = HexColor("#16213e")
SUCCESS       = HexColor("#00b894")
WARNING       = HexColor("#fdcb6e")
INFO          = HexColor("#0984e3")
LIGHT_BG      = HexColor("#f8f9fa")
LIGHT_BLUE    = HexColor("#dfe6e9")
PURPLE        = HexColor("#6c5ce7")
ORANGE        = HexColor("#e17055")
TEAL          = HexColor("#00cec9")
WHITE         = colors.white
BLACK         = colors.black
GREY          = HexColor("#636e72")
LIGHT_GREY    = HexColor("#b2bec3")
SECTION_BG    = HexColor("#edf2f7")
CODE_BG       = HexColor("#2d3436")
CARD_BG       = HexColor("#ffffff")
BORDER_COLOR  = HexColor("#cbd5e0")

# ── Styles ─────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "DocTitle", parent=styles["Title"],
    fontSize=28, leading=34, textColor=PRIMARY,
    spaceAfter=6, alignment=TA_CENTER, fontName="Helvetica-Bold",
)
SUBTITLE_STYLE = ParagraphStyle(
    "DocSubtitle", parent=styles["Normal"],
    fontSize=13, leading=17, textColor=GREY,
    spaceAfter=20, alignment=TA_CENTER, fontName="Helvetica",
)
H1 = ParagraphStyle(
    "H1", parent=styles["Heading1"],
    fontSize=20, leading=26, textColor=PRIMARY,
    spaceBefore=24, spaceAfter=10, fontName="Helvetica-Bold",
    borderWidth=0, borderPadding=0,
)
H2 = ParagraphStyle(
    "H2", parent=styles["Heading2"],
    fontSize=15, leading=20, textColor=ACCENT,
    spaceBefore=16, spaceAfter=8, fontName="Helvetica-Bold",
)
H3 = ParagraphStyle(
    "H3", parent=styles["Heading3"],
    fontSize=12, leading=16, textColor=PURPLE,
    spaceBefore=10, spaceAfter=4, fontName="Helvetica-Bold",
)
BODY = ParagraphStyle(
    "Body", parent=styles["Normal"],
    fontSize=10, leading=14, textColor=HexColor("#2d3436"),
    spaceAfter=6, alignment=TA_JUSTIFY, fontName="Helvetica",
)
BODY_BOLD = ParagraphStyle(
    "BodyBold", parent=BODY,
    fontName="Helvetica-Bold",
)
CODE_STYLE = ParagraphStyle(
    "Code", parent=styles["Code"],
    fontSize=8.5, leading=11, textColor=HexColor("#e8e8e8"),
    backColor=CODE_BG, borderWidth=0.5, borderColor=GREY,
    borderPadding=6, spaceAfter=8, fontName="Courier",
)
LABEL = ParagraphStyle(
    "Label", parent=BODY,
    fontSize=9, textColor=GREY, fontName="Helvetica-Oblique",
)
CALLOUT = ParagraphStyle(
    "Callout", parent=BODY,
    fontSize=10, leading=14, textColor=PRIMARY,
    backColor=HexColor("#ebf5fb"), borderWidth=0.5,
    borderColor=INFO, borderPadding=8, spaceAfter=10,
)
ARROW_STYLE = ParagraphStyle(
    "Arrow", parent=BODY, fontSize=10, leading=14,
    textColor=ACCENT, fontName="Helvetica-Bold", alignment=TA_CENTER,
)

# ── Helpers ────────────────────────────────────────────────────────

def colored_hr(color=ACCENT, width="100%", thickness=2):
    return HRFlowable(width=width, thickness=thickness, color=color,
                      spaceBefore=4, spaceAfter=8)

def section_banner(text, bg=PRIMARY, fg=WHITE):
    """Full-width colored section banner."""
    tbl = Table([[Paragraph(f"<b>{text}</b>",
                            ParagraphStyle("banner", parent=BODY,
                                           fontSize=14, textColor=fg,
                                           fontName="Helvetica-Bold",
                                           alignment=TA_LEFT))]],
                colWidths=["100%"], rowHeights=[32])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return tbl

def io_card(title, input_text, process_text, output_text, explanation):
    """A colorful Input → Process → Output → Why card."""
    data = [
        [Paragraph(f"<b>{title}</b>", ParagraphStyle("ct", parent=BODY, fontSize=12, textColor=WHITE, fontName="Helvetica-Bold"))],
    ]
    header_tbl = Table(data, colWidths=["100%"], rowHeights=[26])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [4, 4, 0, 0]),
    ]))

    rows = []
    labels_vals = [
        ("INPUT", INFO, input_text),
        ("PROCESS", PURPLE, process_text),
        ("OUTPUT", SUCCESS, output_text),
        ("WHY THIS?", ORANGE, explanation),
    ]
    for label, color, text in labels_vals:
        lbl = Paragraph(f'<font color="#{color.hexval()[2:]}">{label}</font>',
                        ParagraphStyle("lbl", parent=BODY, fontSize=9, fontName="Helvetica-Bold"))
        val = Paragraph(text, BODY)
        rows.append([lbl, val])

    body_tbl = Table(rows, colWidths=[75, None])
    body_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, BORDER_COLOR),
        ("ROUNDEDCORNERS", [0, 0, 4, 4]),
    ]))

    wrapper = Table([[header_tbl], [body_tbl]], colWidths=["100%"])
    wrapper.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return KeepTogether([wrapper, Spacer(1, 10)])

def mini_table(headers, rows, col_widths=None, header_bg=PRIMARY):
    """Styled data table."""
    h_style = ParagraphStyle("th", parent=BODY, fontSize=9, textColor=WHITE, fontName="Helvetica-Bold")
    r_style = ParagraphStyle("td", parent=BODY, fontSize=9)

    data = [[Paragraph(h, h_style) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), r_style) for c in row])

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BACKGROUND", (0, 1), (-1, -1), CARD_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
    ]
    # Alternate row colors
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), LIGHT_BG))
    tbl.setStyle(TableStyle(style_cmds))
    return tbl

def arrow_flow(items):
    """Horizontal flow: A → B → C as a single wrapped paragraph."""
    parts = []
    for i, item in enumerate(items):
        parts.append(f'<font color="#{PRIMARY.hexval()[2:]}"><b>{item}</b></font>')
        if i < len(items) - 1:
            parts.append(f'<font color="#e94560"><b> &#8594; </b></font>')
    text = "".join(parts)
    flow_para_style = ParagraphStyle(
        "FlowPara", parent=BODY, fontSize=10, leading=18,
        alignment=TA_CENTER, spaceAfter=8, spaceBefore=4,
        backColor=LIGHT_BG, borderWidth=0.5, borderColor=BORDER_COLOR,
        borderPadding=8,
    )
    return Paragraph(text, flow_para_style)


# ── Page Template ──────────────────────────────────────────────────

def on_page(canvas, doc):
    canvas.saveState()
    # Header line
    canvas.setStrokeColor(PRIMARY)
    canvas.setLineWidth(2)
    canvas.line(40, A4[1] - 40, A4[0] - 40, A4[1] - 40)
    # Header text
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawString(42, A4[1] - 36, "Universal Scraper AI — Architecture Document")
    canvas.drawRightString(A4[0] - 42, A4[1] - 36, datetime.now().strftime("%B %d, %Y"))
    # Footer
    canvas.setStrokeColor(LIGHT_GREY)
    canvas.setLineWidth(0.5)
    canvas.line(40, 35, A4[0] - 40, 35)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawCentredString(A4[0] / 2, 22, f"Page {doc.page}")
    canvas.drawString(42, 22, "Confidential")
    canvas.restoreState()


# ── Build Document ─────────────────────────────────────────────────

def build_pdf():
    output_path = os.path.join(os.path.dirname(__file__), "Universal_Scraper_AI_Architecture.pdf")
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=52, bottomMargin=48,
        leftMargin=40, rightMargin=40,
    )
    story = []

    # ═══════════════════════════════════════════════════════════════
    # COVER PAGE
    # ═══════════════════════════════════════════════════════════════
    story.append(Spacer(1, 100))
    story.append(Paragraph("Universal Scraper AI", TITLE_STYLE))
    story.append(Spacer(1, 6))
    story.append(colored_hr(ACCENT, "60%", 3))
    story.append(Paragraph("Detailed Architecture Documentation", SUBTITLE_STYLE))
    story.append(Spacer(1, 30))

    # Cover info card
    cover_data = [
        ["Version", "2.0 — Hybrid Pipeline"],
        ["Date", datetime.now().strftime("%B %d, %Y")],
        ["Stack", "Python 3.11 · Streamlit · CrewAI · Gemini Flash · Crawl4AI"],
        ["Author", "Engineering Team"],
    ]
    cover_tbl = mini_table(["Property", "Value"], cover_data, col_widths=[120, 350], header_bg=ACCENT2)
    story.append(cover_tbl)
    story.append(Spacer(1, 40))

    story.append(Paragraph(
        "This document provides a comprehensive, component-by-component breakdown of the Universal Scraper AI system. "
        "Each section follows the <b>Input → Process → Output → Why</b> format so reviewers can understand "
        "exactly what each component does, how data flows through the pipeline, and the architectural reasoning behind every decision.",
        CALLOUT))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # TABLE OF CONTENTS
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("TABLE OF CONTENTS", PRIMARY))
    story.append(Spacer(1, 12))

    toc_items = [
        "1. System Overview & High-Level Flow",
        "2. Configuration & Settings",
        "3. Data Models & Schemas",
        "4. Crawler Engine — Multi-Layer Escalation",
        "5. Content Validation — Three-Point Check",
        "6. Schema Inference & Dynamic Model Building",
        "7. Extraction Pipeline — AI-Powered Record Extraction",
        "8. Pagination Detection — Heuristic + AI Fallback",
        "9. Orchestration Pipeline — Two-Phase Architecture",
        "10. Validation Agent — CrewAI Quality Check",
        "11. Auto-Detection Mode",
        "12. Output Logging System",
        "13. UI Components & User Interface",
        "14. Confidence Scoring (Double-Pass)",
        "15. Benchmark & Evaluation System",
        "16. Complete Data Flow Diagram",
        "17. File Reference Map",
    ]
    for item in toc_items:
        story.append(Paragraph(f'<font color="#{PRIMARY.hexval()[2:]}">{item}</font>', BODY))
        story.append(Spacer(1, 2))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # 1. SYSTEM OVERVIEW
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("1. SYSTEM OVERVIEW & HIGH-LEVEL FLOW", PRIMARY))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Universal Scraper AI is a modular, LLM-powered web scraping platform that converts any webpage into structured JSON data. "
        "It combines multi-layer crawling, AI-driven schema inference, intelligent pagination detection, and agent-based validation "
        "into a transparent, auditable pipeline.", BODY))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Three Operational Modes:</b>", BODY_BOLD))
    modes_data = [
        ["Standard Mode", "URL + Description", "Infer schema, crawl, extract, validate, dedup", "Final structured JSON records"],
        ["Two-Phase Mode", "URL + Description", "Phase 1: Crawl + Plan (editable schema) → Phase 2: Extract", "Records with user-refined schema"],
        ["Auto-Detect Mode", "URL only (no description)", "AI detects data types on page → user picks one → extract", "Records from AI-detected structure"],
    ]
    story.append(mini_table(["Mode", "Input", "Process", "Output"], modes_data, col_widths=[90, 95, 195, 100]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>High-Level Pipeline Flow:</b>", BODY_BOLD))
    story.append(Spacer(1, 6))
    flow_items = ["User Input", "Crawl (4 Layers)", "Plan (Schema + Pagination)",
                  "Extract (Chunked)", "Validate (Agent)", "Multi-Page", "Dedup", "Results"]
    story.append(arrow_flow(flow_items))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "<b>Why this architecture?</b> A two-phase design lets users inspect and edit the inferred schema before committing to "
        "expensive extraction. The escalation-based crawler maximizes success rate without wasting credits on easy sites. "
        "Agent-based validation catches extraction errors that simple heuristics miss.", CALLOUT))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # 2. CONFIGURATION
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("2. CONFIGURATION & SETTINGS", TEAL))
    story.append(Spacer(1, 8))

    story.append(io_card(
        "Configuration Module — config.py",
        "<b>Environment variables:</b> GEMINI_API_KEY, SCRAPERAPI_KEY, GEMINI_MODEL (optional overrides)",
        "Loads .env file, applies defaults, exposes a singleton <b>settings</b> object used across all modules. "
        "All thresholds, model names, and API keys are centralized here.",
        "A <b>Settings</b> dataclass with typed attributes (API keys, model name, thresholds, rate-limit params)",
        "Centralizing config prevents magic numbers scattered across files. Environment variable overrides let the same "
        "codebase run in dev/prod without code changes."
    ))

    config_data = [
        ["GEMINI_MODEL", "gemini-3-flash-preview", "LLM model for all AI calls"],
        ["GEMINI_TEMP_STRICT", "0.0", "Deterministic extraction temperature"],
        ["GEMINI_MAX_TOKENS", "8192", "Max output tokens per LLM call"],
        ["MIN_WORDS", "150", "Minimum words for valid crawl content"],
        ["CONTENT_DENSITY_THRESHOLD", "0.3", "Min ratio of non-whitespace to total chars"],
        ["RATE_LIMIT_BASE", "6.0s", "Base delay between page crawls"],
        ["RATE_LIMIT_CAPTCHA_INCREMENT", "+2.0s", "Extra delay per CAPTCHA detected"],
        ["RATE_LIMIT_MAX", "20.0s", "Maximum delay ceiling"],
        ["MAX_PAGES", "10", "Maximum pages for pagination"],
        ["SCRAPERAPI_MIN_CREDITS", "50", "Minimum credits before using proxy layer"],
    ]
    story.append(mini_table(["Setting", "Default", "Purpose"], config_data, col_widths=[165, 105, 210], header_bg=TEAL))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # 3. DATA MODELS
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("3. DATA MODELS & SCHEMAS", PURPLE))
    story.append(Spacer(1, 8))

    story.append(io_card(
        "Data Models — models.py",
        "No runtime input — these are <b>type definitions</b> used throughout the system",
        "Pydantic BaseModel subclasses providing validation, serialization (JSON), and type safety for "
        "all data structures flowing between components.",
        "Importable model classes: FieldSpec, RefinedSchema, PaginationResult, DetectedDataType, DetectedContent, CrawlResult",
        "Pydantic models eliminate entire classes of bugs — invalid types, missing fields, serialization errors. "
        "Every component speaks the same typed language."
    ))

    model_data = [
        ["FieldSpec", "name: str, field_type: str, description: str", "Single field definition (e.g., 'price', 'float', 'Product price in USD')"],
        ["RefinedSchema", "fields: list[FieldSpec], record_description: str", "Complete schema for extraction — defines what to extract"],
        ["PaginationResult", "urls: list[str], pattern: str, method: str", "Detected page URLs and how they were found"],
        ["DetectedDataType", "name, description, record_description, suggested_fields", "AI-detected data structure on a page"],
        ["DetectedContent", "data_types: list[DetectedDataType]", "Container for 1-3 detected types (auto-detect mode)"],
        ["CrawlResult", "url, markdown, success, layer, error, word_count, metadata", "Output of crawling a single page"],
    ]
    story.append(mini_table(["Model", "Key Fields", "Purpose"], model_data, col_widths=[100, 200, 180], header_bg=PURPLE))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # 4. CRAWLER ENGINE
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("4. CRAWLER ENGINE — MULTI-LAYER ESCALATION", ACCENT))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "The crawler is the foundation of the system. Instead of a single approach, it uses a <b>4-layer escalation strategy</b> "
        "that starts with the lightest technique and progressively upgrades to more aggressive methods only when needed.", BODY))
    story.append(Spacer(1, 8))

    story.append(io_card(
        "Crawler Engine — crawler/engine.py",
        "<b>URL</b> (string) + optional callback function for progress updates",
        "Iterates through Layers 1→4. Each layer attempts to crawl the URL and convert HTML to Markdown. "
        "After each attempt, a <b>3-point validation</b> check determines success. If validation fails, the engine "
        "escalates to the next layer. Tracks full escalation history.",
        "<b>CrawlResult</b>: url, markdown (cleaned text), success (bool), layer (1-4), error, word_count, metadata",
        "Escalation over retry — trying progressively different techniques is more effective than retrying the same one. "
        "Light layers (1-2) are free and fast; heavy layers (3-4) use paid APIs but handle tough sites."
    ))

    story.append(Paragraph("<b>The Four Layers:</b>", H2))
    layer_data = [
        ["Layer 1", "Stealth Crawler", "Crawl4AI + magic mode + JS execution + 3s delay",
         "Free, fast, handles ~70% of sites", "crawler/layer1_stealth.py"],
        ["Layer 2", "Undetected Crawler", "Crawl4AI + stealth hardening + user simulation + navigator override",
         "Bypasses basic bot detection", "crawler/layer2_undetected.py"],
        ["Layer 3", "Proxy Crawler", "ScraperAPI residential proxies + 3 retries + HTML→Markdown conversion",
         "Bypasses IP bans and geo-blocks. Checks credit balance first (min 50).", "crawler/layer3_proxy.py"],
        ["Layer 4", "Jina Fallback", "Jina Reader API (r.jina.ai) + 3 retries + exponential backoff",
         "Last resort, no credentials needed, works on most public pages", "crawler/layer4_jina.py"],
    ]
    story.append(mini_table(
        ["Layer", "Name", "Technique", "Why This Layer", "File"],
        layer_data, col_widths=[45, 80, 140, 140, 80], header_bg=ACCENT))

    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Escalation Flow:</b>", BODY_BOLD))
    story.append(arrow_flow(["Layer 1 (Stealth)", "Validate?", "Layer 2 (Undetected)",
                             "Validate?", "Layer 3 (Proxy)", "Validate?", "Layer 4 (Jina)"]))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # 5. CONTENT VALIDATION
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("5. CONTENT VALIDATION — THREE-POINT CHECK", WARNING))
    story.append(Spacer(1, 8))

    story.append(io_card(
        "Content Validator — crawler/validator.py",
        "<b>Raw markdown text</b> returned by any crawler layer",
        "Runs three independent checks in sequence:<br/>"
        "1. <b>Word Count</b> — Content must have ≥ 150 words<br/>"
        "2. <b>Block Phrase Scan</b> — Checks first 500 chars for protection signatures (403, CAPTCHA, 'access denied', 'enable javascript', etc.)<br/>"
        "3. <b>Content Density</b> — Ratio of non-whitespace to total characters must be ≥ 0.3",
        "<b>Boolean</b>: True (content is valid) or False (trigger escalation to next layer)",
        "Without validation, the system would accept bot-protection pages or empty shells as 'successful' crawls. "
        "The 3-point check catches blocked responses, CAPTCHA pages, and garbled output that would produce garbage extractions."
    ))

    check_data = [
        ["Word Count", "len(text.split()) >= 150", "Rejects empty/stub pages", "150 words"],
        ["Block Phrases", "Scan first 500 chars for 12+ known phrases", "Catches CAPTCHA, 403, bot walls", "12 phrase patterns"],
        ["Content Density", "non_whitespace / total_chars >= 0.3", "Rejects whitespace-heavy garbage", "0.3 ratio"],
    ]
    story.append(mini_table(["Check", "Logic", "Catches", "Threshold"], check_data, col_widths=[85, 155, 130, 100], header_bg=HexColor("#f39c12")))

    story.append(Spacer(1, 10))

    # Risk Classifier
    story.append(io_card(
        "Risk Classifier — crawler/classifier.py",
        "<b>URL</b> (string) — performs a lightweight HEAD request",
        "Analyzes HTTP response for risk signals:<br/>"
        "• <b>HIGH</b>: Known protected domains (LinkedIn, Amazon, Zillow), 403 status, 503 challenge<br/>"
        "• <b>MEDIUM</b>: Cloudflare headers detected, >2 redirects<br/>"
        "• <b>LOW</b>: None of the above",
        "<b>Risk level string</b>: 'LOW', 'MEDIUM', or 'HIGH' — informs starting layer selection",
        "Pre-classifying risk avoids wasting time on layers that will definitely fail for protected sites."
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # 6. SCHEMA INFERENCE
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("6. SCHEMA INFERENCE & DYNAMIC MODEL BUILDING", INFO))
    story.append(Spacer(1, 8))

    story.append(io_card(
        "Prompt Refiner — extraction/prompt_refiner.py",
        "<b>User description</b> (e.g., 'job listings with salary and company') + <b>sample content</b> (first ~10K chars of crawled markdown, smart-sampled: beginning + middle + end)",
        "Sends description + content sample to Gemini with a system prompt instructing it to:<br/>"
        "• Infer 4-10 fields in snake_case<br/>"
        "• Each field gets a type (str/int/float/list[str]) and description<br/>"
        "• Generate a record_description explaining what one record represents<br/>"
        "Smart sampling takes beginning (0-3333), middle (~50%), and end portions to avoid nav-heavy headers/footers.",
        "<b>RefinedSchema</b>: list of FieldSpec objects + record_description",
        "The LLM sees actual page content alongside the user's intent, so it can infer fields that actually exist "
        "on the page rather than hallucinating fields. Smart sampling ensures representative content without hitting token limits."
    ))

    story.append(Spacer(1, 6))

    story.append(io_card(
        "Dynamic Model Builder — extraction/schema_builder.py",
        "<b>RefinedSchema</b> (list of fields with types)",
        "Uses Pydantic's <b>create_model()</b> to dynamically generate a BaseModel class at runtime:<br/>"
        "• All fields are typed as <b>str</b> with default 'NOT_FOUND' (Gemini workaround)<br/>"
        "• Post-processing converts values to target types (int, float, list[str])<br/>"
        "• Currency symbols, commas, percentages are stripped for numeric conversion<br/>"
        "• Lists parsed from JSON arrays, semicolons, or smart comma-splitting<br/>"
        "• Records with &lt;25% field fill rate are filtered out",
        "<b>Pydantic BaseModel class</b> ready for structured extraction with Instructor library",
        "Gemini struggles with strict typed JSON output — using str for everything and post-processing "
        "gives much higher extraction success rates. The 25% filter removes garbage partial records."
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # 7. EXTRACTION PIPELINE
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("7. EXTRACTION PIPELINE — AI-POWERED RECORD EXTRACTION", SUCCESS))
    story.append(Spacer(1, 8))

    story.append(io_card(
        "Record Extractor — extraction/extractor.py",
        "<b>Markdown content</b> + <b>Pydantic model</b> (from schema builder) + <b>record_description</b> + optional schema for field instructions",
        "Two strategies based on content size:<br/><br/>"
        "<b>Small content (≤100KB):</b> Single batch extraction — send all content to Gemini in one call<br/><br/>"
        "<b>Large content (&gt;100KB):</b> Smart chunking pipeline —<br/>"
        "1. <b>Boundary Detection</b>: Ask Gemini to identify line numbers where records start<br/>"
        "2. <b>Chunk Splitting</b>: Split markdown at detected boundaries<br/>"
        "3. <b>Parallel Extraction</b>: 3 concurrent workers extract from each chunk<br/>"
        "4. <b>Fallback</b>: If &gt;50% chunks fail, retry with single batch extraction<br/><br/>"
        "Uses <b>Instructor library</b> for structured JSON output. Prompt includes explicit rules: "
        "fill every field, use 'NOT_FOUND' only when genuinely missing, strip HTML, preserve 'N/A'/'TBD'.",
        "<b>List of dicts</b> — each dict is one extracted record with all schema fields populated",
        "Smart chunking prevents token overflow on large pages while maintaining record integrity. "
        "Boundary detection ensures chunks don't split records in half. Parallel extraction speeds up large jobs 3x."
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Extraction Strategy Decision:</b>", BODY_BOLD))
    ext_data = [
        ["≤ 100KB", "Batch", "Single Gemini call with all content", "Simple, reliable for most pages"],
        ["> 100KB", "Chunked", "Boundary detect → split → 3 parallel workers", "Prevents token overflow, 3x faster"],
        ["> 50% chunk fail", "Fallback", "Retry as single batch extraction", "Safety net for edge cases"],
    ]
    story.append(mini_table(["Content Size", "Strategy", "Process", "Reason"],
                            ext_data, col_widths=[75, 65, 195, 145], header_bg=SUCCESS))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # 8. PAGINATION
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("8. PAGINATION DETECTION — HEURISTIC + AI FALLBACK", ORANGE))
    story.append(Spacer(1, 8))

    story.append(io_card(
        "Heuristic Pagination — pagination/heuristic.py",
        "<b>URL</b> + <b>num_pages</b> (requested) + optional <b>markdown</b> content",
        "Three-step detection (zero AI calls):<br/>"
        "1. <b>Site-specific patterns</b>: Known rules for Google Scholar (?start=N×10), Naukri (?page=N), Flipkart (?page=N), LinkedIn (?start=N×25)<br/>"
        "2. <b>URL parameter detection</b>: Check for existing page/offset params and increment them<br/>"
        "3. <b>Generic fallback</b>: Append ?page=N — marked as 'speculative'",
        "<b>PaginationResult</b>: list of page URLs + pattern description + method ('heuristic')",
        "Heuristic detection is instant and free. Site-specific patterns guarantee correct pagination for popular targets. "
        "Marking speculative results triggers the AI fallback for smarter detection."
    ))
    story.append(Spacer(1, 6))

    story.append(io_card(
        "AI Pagination Fallback — pagination/ai_fallback.py",
        "<b>URL</b> + <b>markdown</b> (page content) + <b>num_pages</b> — triggered only when heuristic result is 'speculative'",
        "Asks Gemini to analyze the page content and find:<br/>"
        "• 'Next page' links<br/>"
        "• Numbered pagination links<br/>"
        "• 'Load more' buttons<br/>"
        "Resolves relative URLs to absolute using urljoin.",
        "<b>PaginationResult</b>: refined list of actual page URLs + pattern + method ('ai_fallback')",
        "AI can find pagination patterns that heuristics miss — JavaScript-rendered pagination, "
        "non-standard URL schemes, or pagination embedded in link text rather than URL parameters."
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Adaptive Rate Limiter (pagination/rate_limiter.py):</b>", H3))
    story.append(Paragraph(
        "Prevents getting blocked during multi-page crawls. Base delay of 6s between requests. "
        "+2s per CAPTCHA detected (cumulative). -0.5s per successful request (decay). Max ceiling of 20s. "
        "Reports current delay via callback for UI display.", BODY))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # 9. ORCHESTRATION PIPELINE
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("9. ORCHESTRATION PIPELINE — TWO-PHASE ARCHITECTURE", PRIMARY))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "The pipeline is split into two independent phases, allowing the user to inspect and edit "
        "the schema between crawl and extraction.", BODY))
    story.append(Spacer(1, 8))

    story.append(io_card(
        "Phase 1-2: run_crawl_and_plan() — agents/crew.py",
        "<b>URL</b>, <b>description</b> (optional), <b>num_pages</b>, optional pre-built <b>schema</b>, <b>callback</b>",
        "<b>Phase 1 — Crawl:</b><br/>"
        "• Create CrawlerEngine and crawl the first page<br/>"
        "• Save markdown to output/ (backward compat) AND output_logs/{slug}_{ts}/page_1.txt<br/>"
        "• Create run directory for structured logging<br/><br/>"
        "<b>Phase 2 — Plan (parallel):</b><br/>"
        "• ThreadPoolExecutor(max_workers=2) runs schema inference + pagination detection simultaneously<br/>"
        "• Schema inference: 60s timeout → refine_prompt() → RefinedSchema<br/>"
        "• Pagination: 30s timeout → detect_pagination() → PaginationResult<br/>"
        "• If heuristic result is 'speculative' and num_pages &gt; 1: AI pagination fallback",
        "<b>Dict</b>: markdown, txt_path, crawl_info, schema, page_urls, pagination_result, engine, telemetry, run_dir",
        "Parallel schema + pagination saves ~30-60s on every run. Returning everything in a dict lets "
        "the UI display intermediate results and offer the schema editor before committing to extraction."
    ))
    story.append(Spacer(1, 6))

    story.append(io_card(
        "Phase 3-6: run_extract_and_validate() — agents/crew.py",
        "<b>plan_result dict</b> (from Phase 1-2) + <b>num_pages</b> + <b>callback</b>",
        "<b>Phase 3 — Extract:</b> Extract records from page 1 markdown using schema<br/>"
        "<b>Phase 4 — Validate:</b> CrewAI Validator Agent checks quality (see next section)<br/>"
        "<b>Phase 5 — Multi-page:</b> If num_pages &gt; 1, crawl + extract remaining pages in parallel (3 workers)<br/>"
        "<b>Phase 6 — Dedup:</b> Exact-match duplicate removal across all pages<br/><br/>"
        "Throughout: saves page_N.txt, page_N.json, merged.txt, merged.json, deduped.json to run_dir",
        "<b>Dict</b>: records (final list[dict]), schema (JSON), crawl_info (per-page details), telemetry (full metrics)",
        "Separating extraction from crawl+plan lets the user edit the schema. Multi-page extraction runs in parallel "
        "for speed. Structured logging at every stage enables debugging and auditability."
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # 10. VALIDATION AGENT
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("10. VALIDATION AGENT — CrewAI QUALITY CHECK", ACCENT))
    story.append(Spacer(1, 8))

    story.append(io_card(
        "Validator Agent — Phase 4 in agents/crew.py",
        "<b>Extracted records</b> (JSON array) from Phase 3",
        "Creates a CrewAI Agent with role 'Quality Validator':<br/>"
        "1. Agent receives records as JSON string<br/>"
        "2. Agent calls <b>ValidateTool</b> which checks:<br/>"
        "   — Empty/None/'NOT_FOUND' fields per column<br/>"
        "   — Exact duplicate records<br/>"
        "   — Issues list (all-empty fields, high duplicate count)<br/>"
        "3. Agent reviews validation report and returns cleaned records<br/>"
        "4. Timeout: 90 seconds → fallback to unvalidated records",
        "<b>Cleaned records</b> (JSON array) — or original records if agent fails/times out",
        "An LLM-based validator can catch semantic issues that rule-based checks miss — e.g., prices in name fields, "
        "truncated descriptions, inconsistent formatting. The 90s timeout ensures the pipeline never hangs."
    ))

    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>ValidateTool Output Format:</b>", H3))
    val_fields = [
        ["total_records", "int", "Number of records checked"],
        ["empty_field_counts", "dict", "Per-field count of None/empty/'NOT_FOUND' values"],
        ["duplicate_count", "int", "Number of exact-duplicate records"],
        ["issues", "list[str]", "Human-readable issue descriptions"],
        ["valid", "bool", "True if ≤ 2 issues found"],
    ]
    story.append(mini_table(["Field", "Type", "Description"], val_fields, col_widths=[120, 60, 300], header_bg=ACCENT))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # 11. AUTO-DETECTION MODE
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("11. AUTO-DETECTION MODE", PURPLE))
    story.append(Spacer(1, 8))

    story.append(io_card(
        "Content Auto-Detector — extraction/auto_detect.py",
        "<b>Crawled markdown</b> (from Phase 1 crawl) — no user description needed",
        "Two-tier detection:<br/>"
        "1. <b>CrewAI Agent</b> (Content Analyst) with AnalyzeContentTool — 60s timeout<br/>"
        "2. <b>Direct Gemini fallback</b> if agent times out<br/><br/>"
        "Agent/Gemini analyzes the page and identifies 1-3 main repeating data structures. "
        "For each: generates a name, description, record_description, and 4-10 suggested fields.",
        "<b>List of DetectedDataType</b> objects — user picks one in the UI, which becomes the schema for extraction",
        "Auto-detect enables 'zero-config' scraping — the user just pastes a URL. "
        "Detecting multiple data types handles pages with mixed content (e.g., products + reviews). "
        "The CrewAI agent adds reasoning, but the direct fallback ensures reliability."
    ))

    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Auto-Detect → Extraction Flow:</b>", BODY_BOLD))
    story.append(arrow_flow(["Crawl URL", "AI Detect Types", "User Picks Type",
                             "Convert to Schema", "Schema Editor", "Extract"]))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # 12. OUTPUT LOGGING
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("12. OUTPUT LOGGING SYSTEM", TEAL))
    story.append(Spacer(1, 8))

    story.append(io_card(
        "Structured Run Logs — agents/crew.py",
        "All pipeline artifacts generated during a run",
        "Each run creates <b>output_logs/{url_slug}_{timestamp}/</b> containing:<br/>"
        "• <b>page_N.txt</b> — Raw markdown from each crawled page<br/>"
        "• <b>page_N.json</b> — Extracted records from each page individually<br/>"
        "• <b>merged.txt</b> — All page markdowns concatenated with '--- PAGE N ---' separators<br/>"
        "• <b>merged.json</b> — All records combined (pre-deduplication)<br/>"
        "• <b>deduped.json</b> — Final records after exact-match deduplication<br/><br/>"
        "Single-page runs: merged.txt = page_1.txt content, merged.json = page_1.json content",
        "<b>Directory</b> with 5+ files per run — full audit trail on disk",
        "Full transparency: reviewers can inspect every stage — did the crawl get good content? "
        "Did extraction work per-page? How many dupes were removed? The old output/ folder is also preserved for backward compatibility."
    ))

    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Directory Structure Example (3-page run):</b>", BODY_BOLD))
    dir_data = [
        ["page_1.txt", "Raw markdown from page 1", "After crawl"],
        ["page_2.txt", "Raw markdown from page 2", "During multi-page"],
        ["page_3.txt", "Raw markdown from page 3", "During multi-page"],
        ["page_1.json", "Extracted records from page 1", "After extraction"],
        ["page_2.json", "Extracted records from page 2", "During multi-page"],
        ["page_3.json", "Extracted records from page 3", "During multi-page"],
        ["merged.txt", "All 3 pages concatenated with separators", "Before dedup"],
        ["merged.json", "All records from all pages combined", "Before dedup"],
        ["deduped.json", "Final unique records", "After dedup"],
    ]
    story.append(mini_table(["File", "Contents", "Created At Stage"],
                            dir_data, col_widths=[90, 230, 140], header_bg=TEAL))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # 13. UI COMPONENTS
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("13. UI COMPONENTS & USER INTERFACE", INFO))
    story.append(Spacer(1, 8))

    ui_data = [
        ["Sidebar", "ui/sidebar.py",
         "Mode toggle, URL input, description, pages slider, presets, Run button",
         "Central control panel for all user inputs"],
        ["Progress Feed", "ui/progress_feed.py",
         "3-zone dashboard: Phase stepper (●/✓/✗/○), Metrics panel (live counters), Activity log (real-time steps)",
         "Real-time feedback during scraping — users see exactly what's happening"],
        ["Results Table", "ui/results_table.py",
         "Pandas DataFrame display — lists flattened to comma-separated, None→'—', all string cast",
         "Clean tabular view of extracted data"],
        ["Quality Dashboard", "ui/quality_dashboard.py",
         "Per-field fill rates (%), complete records count, completeness distribution chart, color-coded status",
         "Instant quality assessment without manual inspection"],
        ["Schema Editor", "ui/schema_editor.py",
         "Editable form: field name/type/description, delete checkbox, add new field, validation",
         "User control over extraction schema — fix AI mistakes before extraction"],
        ["Export", "ui/export.py",
         "Download buttons for JSON and CSV. CSV flattens list columns.",
         "One-click data export in common formats"],
        ["Transparency Panel", "ui/transparency_panel.py",
         "7 expandable sections: Risk, Escalation timeline, Schema intel, Pagination, Extraction, Dedup, Timings",
         "Full pipeline audit trail for judges and debugging"],
        ["Chat Panel", "ui/chat_panel.py",
         "Q&A interface over records (capped at 50). Gemini-powered analysis with conversation history.",
         "Ask questions about extracted data in natural language"],
        ["Insights Tab", "ui/insights_tab.py",
         "Auto-generated analysis: numeric stats, list stats, text frequency, outlier detection",
         "Automated data profiling without manual analysis"],
    ]
    story.append(mini_table(
        ["Component", "File", "What It Does", "Why"],
        ui_data, col_widths=[75, 95, 195, 115], header_bg=INFO))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # 14. CONFIDENCE SCORING
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("14. CONFIDENCE SCORING — DOUBLE-PASS EXTRACTION", PURPLE))
    story.append(Spacer(1, 8))

    story.append(io_card(
        "Confidence Scorer — extraction/confidence.py",
        "<b>Markdown</b> + <b>record_model</b> + <b>record_description</b> (same as normal extraction)",
        "Runs extraction <b>twice</b> with different temperatures:<br/>"
        "1. <b>Run 1 (temp=0.0)</b>: Strict, deterministic extraction<br/>"
        "2. <b>Run 2 (temp=0.7)</b>: Creative, varied extraction<br/>"
        "3. <b>Alignment</b>: Match records across runs via field similarity<br/>"
        "   — Primary key auto-detected (first field with &gt;80% unique values, gets 3× weight)<br/>"
        "4. <b>Per-field scoring</b>: SequenceMatcher ratio between matched records<br/>"
        "   — Both None → 0.95 | One None → 0.3 | Exact match → 1.0 | Fuzzy → ratio",
        "<b>Records</b> + <b>confidence_scores</b> (list of {field: float} dicts, 0.0–1.0 per field per record)",
        "If two different temperature settings produce the same value for a field, we can be confident it's correct. "
        "Disagreements highlight uncertain extractions that may need manual review."
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # 15. BENCHMARK
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("15. BENCHMARK & EVALUATION SYSTEM", ORANGE))
    story.append(Spacer(1, 8))

    story.append(io_card(
        "Benchmark Comparator — benchmark/comparator.py",
        "<b>Predicted records</b> (from pipeline) + <b>Ground truth records</b> (manually curated)",
        "Fuzzy-match evaluation:<br/>"
        "1. Greedy matching: Each predicted record matched to best ground truth record<br/>"
        "2. Field similarity: fuzzywuzzy token_sort_ratio (threshold: 75%)<br/>"
        "3. Record match: At least 30% of fields must match<br/>"
        "4. Compute Precision, Recall, F1 overall and per-field",
        "<b>Results dict</b>: overall P/R/F1, per-field P/R/F1 — saved to benchmark/results.json",
        "Fuzzy matching handles minor formatting differences (e.g., '$100' vs '100', 'Inc.' vs 'Inc'). "
        "Per-field metrics reveal which fields are hardest to extract correctly."
    ))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # 16. COMPLETE DATA FLOW
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("16. COMPLETE DATA FLOW DIAGRAM", PRIMARY))
    story.append(Spacer(1, 8))

    flow_style = ParagraphStyle("flow", parent=BODY, fontSize=9, leading=12, fontName="Courier")
    flow_text = """<font color="#0f3460"><b>
USER INPUT (Sidebar)
│
├─ Standard Mode ──────────────────────────────┐
│   URL + Description + Pages                  │
│                                              ▼
├─ Two-Phase Mode ──────────── run_crawl_and_plan()
│   URL + Description + Pages      │
│                                  ├─ CrawlerEngine.crawl()
├─ Auto-Detect Mode                │   └─ Layer 1 → 2 → 3 → 4
│   URL only                       │   └─ Validation (3-point)
│                                  │
│                                  ├─ [PARALLEL]
│                                  │   ├─ refine_prompt() → Schema
│                                  │   └─ detect_pagination() → URLs
│                                  │
│                                  ├─ AI pagination fallback (if speculative)
│                                  │
│                                  └─ Returns: plan_result dict
│                                              │
│  [User edits schema if Two-Phase]            │
│                                              ▼
│                              run_extract_and_validate()
│                                  │
│                                  ├─ Phase 3: extract_records()
│                                  │   ├─ ≤100KB → batch
│                                  │   └─ &gt;100KB → boundary detect → chunk → parallel
│                                  │
│                                  ├─ Phase 4: Validator Agent (CrewAI)
│                                  │   └─ ValidateTool → cleaned records
│                                  │
│                                  ├─ Phase 5: Multi-page (if pages &gt; 1)
│                                  │   └─ 3 parallel workers: crawl + extract per page
│                                  │
│                                  ├─ Phase 6: deduplicate_records()
│                                  │
│                                  └─ Save: page_N.txt/json, merged.*, deduped.json
│                                              │
│                                              ▼
│                                     RESULTS DISPLAY
│                                  ├─ Results Table
│                                  ├─ Quality Dashboard
│                                  ├─ Transparency Panel
│                                  ├─ Insights Tab
│                                  ├─ Chat Panel
│                                  └─ Export (JSON/CSV)
</b></font>"""
    story.append(Paragraph(flow_text, flow_style))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════
    # 17. FILE REFERENCE MAP
    # ═══════════════════════════════════════════════════════════════
    story.append(section_banner("17. FILE REFERENCE MAP", ACCENT2))
    story.append(Spacer(1, 8))

    file_data = [
        ["Entry Point", "app.py", "Streamlit application — routes user actions to pipeline"],
        ["Config", "config.py", "Centralized settings, API keys, thresholds"],
        ["Models", "models.py", "Pydantic data models (FieldSpec, RefinedSchema, etc.)"],
        ["Crawler Engine", "crawler/engine.py", "Multi-layer escalation orchestrator"],
        ["Crawler Base", "crawler/base.py", "Abstract base class for all crawler layers"],
        ["Layer 1", "crawler/layer1_stealth.py", "Crawl4AI stealth mode + magic mode"],
        ["Layer 2", "crawler/layer2_undetected.py", "Crawl4AI undetected mode + user simulation"],
        ["Layer 3", "crawler/layer3_proxy.py", "ScraperAPI residential proxy crawler"],
        ["Layer 4", "crawler/layer4_jina.py", "Jina Reader API fallback"],
        ["Validator", "crawler/validator.py", "Three-point content validation"],
        ["Classifier", "crawler/classifier.py", "Risk level classification (HEAD request)"],
        ["Extractor", "extraction/extractor.py", "AI extraction with smart chunking"],
        ["Schema Builder", "extraction/schema_builder.py", "Dynamic Pydantic model creation"],
        ["Prompt Refiner", "extraction/prompt_refiner.py", "LLM-based schema inference"],
        ["Auto-Detect", "extraction/auto_detect.py", "Content type detection (zero-config mode)"],
        ["Confidence", "extraction/confidence.py", "Double-pass confidence scoring"],
        ["Heuristic Pag.", "pagination/heuristic.py", "Rule-based pagination URL generation"],
        ["AI Pagination", "pagination/ai_fallback.py", "LLM-based pagination detection"],
        ["Rate Limiter", "pagination/rate_limiter.py", "Adaptive delay between requests"],
        ["Pipeline", "agents/crew.py", "Two-phase orchestration + output logging"],
        ["Direct Mode", "agents/direct_mode.py", "Simplified deterministic pipeline"],
        ["Tools", "agents/tools.py", "CrewAI tool wrappers"],
        ["Sidebar", "ui/sidebar.py", "Input controls and presets"],
        ["Progress", "ui/progress_feed.py", "Real-time 3-zone progress dashboard"],
        ["Results", "ui/results_table.py", "Data table display"],
        ["Quality", "ui/quality_dashboard.py", "Fill rate and completeness analysis"],
        ["Schema Editor", "ui/schema_editor.py", "Interactive schema modification"],
        ["Export", "ui/export.py", "JSON/CSV download buttons"],
        ["Transparency", "ui/transparency_panel.py", "Pipeline audit trail"],
        ["Chat", "ui/chat_panel.py", "Q&A over extracted records"],
        ["Insights", "ui/insights_tab.py", "Auto-generated data analysis"],
        ["Benchmark", "benchmark/comparator.py", "Fuzzy-match evaluation vs ground truth"],
        ["Logger", "utils/logger.py", "Structured logging utility"],
    ]
    story.append(mini_table(
        ["Category", "File", "Purpose"],
        file_data, col_widths=[85, 155, 240], header_bg=ACCENT2))

    story.append(Spacer(1, 20))
    story.append(colored_hr(PRIMARY, "100%", 2))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "<i>End of Architecture Document — Universal Scraper AI v2.0</i>",
        ParagraphStyle("footer", parent=BODY, alignment=TA_CENTER, textColor=GREY, fontName="Helvetica-Oblique")))

    # ── Build ──────────────────────────────────────────────────────
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF generated: {output_path}")
    return output_path


if __name__ == "__main__":
    build_pdf()
