"""Live progress dashboard with three-zone layout."""

import time
import threading
import streamlit as st


PHASE_ORDER = ["crawl", "plan", "extract", "validate", "complete"]

PHASE_CONFIG = {
    "crawl":    {"icon": "🌐", "label": "Crawl"},
    "plan":     {"icon": "🧠", "label": "Plan"},
    "extract":  {"icon": "⛏️",  "label": "Extract"},
    "validate": {"icon": "✅", "label": "Validate"},
    "complete": {"icon": "🏁", "label": "Done"},
}

PHASE_MAP = {
    # Crawl phase
    "crawl_first_page": "crawl", "crawl_start": "crawl",
    "layer_attempt": "crawl", "layer_failed": "crawl",
    "crawl_success": "crawl", "crawl_failed": "crawl",
    "crawl_complete": "crawl", "crew_starting": "crawl",
    # Plan phase
    "planning_start": "plan", "refining_prompt": "plan",
    "prompt_refined": "plan", "building_schema": "plan",
    "detecting_pagination": "plan", "pagination_detected": "plan",
    "planning_complete": "plan", "planning_fallback": "plan",
    "auto_detect_start": "plan", "auto_detect_complete": "plan",
    # Extract phase
    "extraction_start": "extract", "extraction_batch": "extract",
    "extraction_batch_done": "extract", "boundary_detection": "extract",
    "boundary_detected": "extract", "boundary_fallback": "extract",
    "chunk_extracting": "extract", "chunk_extracted": "extract",
    "chunk_majority_fallback": "extract",
    "extracting": "extract",
    "extraction_complete": "extract",
    "multi_page_start": "extract", "processing_page": "extract",
    "page_extracted": "extract", "page_failed": "extract",
    "rate_limit_wait": "extract", "rate_limit_captcha": "extract",
    # Validate phase
    "validation_start": "validate", "validation_complete": "validate",
    "validation_fallback": "validate",
    # Complete
    "crew_complete": "complete", "complete": "complete",
    "crew_running": "extract", "crew_elapsed": "extract",
}

STEP_ICONS = {
    "crawl_start": "🌐", "layer_attempt": "🔄", "layer_failed": "❌",
    "crawl_success": "✅", "crawl_complete": "✅", "crawl_failed": "💥",
    "planning_start": "🧠", "planning_complete": "🧠", "refining_prompt": "🔬",
    "building_schema": "🧬", "detecting_pagination": "📄", "pagination_detected": "📄",
    "extraction_start": "⛏️", "extraction_complete": "⛏️",
    "chunk_extracting": "🔨", "chunk_extracted": "✅",
    "boundary_detection": "🔍", "boundary_detected": "🔍",
    "processing_page": "📃", "page_extracted": "📃", "page_failed": "❌",
    "multi_page_start": "📚",
    "validation_start": "🔎", "validation_complete": "✅", "validation_fallback": "⚠️",
    "rate_limit_wait": "⏳", "rate_limit_captcha": "🛡️",
    "crew_starting": "🚀", "crew_complete": "🏁", "complete": "🏁",
    "error": "❗",
}


class ProgressFeed:
    """Three-zone live progress dashboard for pipeline execution."""

    STEP_LABELS = {
        "crawl_first_page": "Crawling first page...",
        "crawl_start": "Starting crawler...",
        "layer_attempt": "Trying crawler layer...",
        "layer_failed": "Layer failed, escalating...",
        "crawl_success": "Crawl successful!",
        "crawl_failed": "All layers failed",
        "crawl_complete": "Crawl complete",
        "refining_prompt": "Refining extraction schema...",
        "prompt_refined": "Schema ready",
        "building_schema": "Building dynamic model...",
        "detecting_pagination": "Detecting pagination...",
        "pagination_detected": "Pagination detected",
        "planning_start": "Planning extraction...",
        "planning_complete": "Plan ready",
        "planning_fallback": "Planning fallback to direct call",
        "processing_page": "Processing page...",
        "extraction_start": "Starting extraction...",
        "extraction_complete": "Extraction complete",
        "extracting": "Extracting records...",
        "page_extracted": "Page extraction complete",
        "page_failed": "Page failed",
        "validation_start": "Validating records...",
        "validation_complete": "Validation complete",
        "validation_fallback": "Validation skipped",
        "multi_page_start": "Starting multi-page scrape...",
        "complete": "Pipeline complete!",
        "error": "Error occurred",
        "extraction_batch": "Extracting records (single batch)...",
        "extraction_batch_done": "Batch extraction complete",
        "boundary_detection": "Detecting record boundaries...",
        "boundary_detected": "Record boundaries found",
        "boundary_fallback": "Boundary detection failed, using batch fallback",
        "chunk_extracting": "Extracting chunk...",
        "chunk_extracted": "Chunk extraction complete",
        "chunk_majority_fallback": "Too many chunk failures, using batch fallback",
        "rate_limit_wait": "Rate limiting...",
        "rate_limit_captcha": "CAPTCHA detected, increasing delay",
        "crew_starting": "Starting pipeline...",
        "crew_running": "Pipeline working...",
        "crew_elapsed": "Pipeline still working...",
        "crew_complete": "Pipeline finished!",
        "auto_detect_start": "Analyzing page content...",
        "auto_detect_complete": "Content analysis complete",
    }

    def __init__(self, start_phase="crawl"):
        self.start_time = time.time()
        self.steps = []
        self._lock = threading.Lock()

        # Phase tracking
        self.current_phase = start_phase
        self.phase_status = {p: "pending" for p in PHASE_ORDER}
        self.phase_status[start_phase] = "active"

        # Mark earlier phases as complete when starting mid-pipeline
        for p in PHASE_ORDER:
            if p == start_phase:
                break
            self.phase_status[p] = "complete"

        # Metrics tracking
        self.metrics = {
            "records": 0,
            "pages_done": 0,
            "pages_total": 1,
            "fields": 0,
            "words": 0,
            "chunks_done": 0,
            "chunks_total": 0,
            "layer": 0,
        }

        # Zone 1: Phase stepper
        self.wrapper = st.container()
        with self.wrapper:
            self.stepper_placeholder = st.empty()

            # Zone 2: Live metrics
            metric_cols = st.columns(4)
            self.metric_placeholders = [col.empty() for col in metric_cols]

            # Progress bar
            self.progress_placeholder = st.empty()

            # Zone 3: Activity log
            self.container = st.status("Initializing...", expanded=True)

        # Render initial state
        self._render_stepper()
        self._render_metrics()

    def _render_stepper(self):
        """Render the phase stepper bar into Zone 1."""
        with self.stepper_placeholder.container():
            cols = st.columns(len(PHASE_ORDER) * 2 - 1)
            for i, phase in enumerate(PHASE_ORDER):
                col_idx = i * 2
                status = self.phase_status[phase]
                cfg = PHASE_CONFIG[phase]

                if status == "active":
                    text = f":blue[● **{cfg['label']}**]"
                elif status == "complete":
                    text = f":green[✓ {cfg['label']}]"
                elif status == "error":
                    text = f":red[✗ {cfg['label']}]"
                else:
                    text = f":gray[○ {cfg['label']}]"

                cols[col_idx].markdown(text)

                # Arrow between phases
                if i < len(PHASE_ORDER) - 1:
                    cols[col_idx + 1].markdown(
                        "<div style='text-align:center;padding-top:4px;color:#888'>→</div>",
                        unsafe_allow_html=True,
                    )

    def _render_metrics(self):
        """Render 4 metric cards into Zone 2, adapting to current phase."""
        elapsed = time.time() - self.start_time
        m = self.metrics
        phase = self.current_phase

        if phase == "crawl":
            self.metric_placeholders[0].metric("Layer", m["layer"] or "—")
            self.metric_placeholders[1].metric("Words", f"{m['words']:,}" if m["words"] else "—")
            self.metric_placeholders[2].metric("Elapsed", f"{elapsed:.0f}s")
            self.metric_placeholders[3].metric("Phase", "Crawling")
        elif phase == "plan":
            self.metric_placeholders[0].metric("Fields", m["fields"] or "—")
            self.metric_placeholders[1].metric("Pages Found", m["pages_total"])
            self.metric_placeholders[2].metric("Elapsed", f"{elapsed:.0f}s")
            self.metric_placeholders[3].metric("Phase", "Planning")
        elif phase == "extract":
            self.metric_placeholders[0].metric("Records", m["records"])
            pages_label = f"{m['pages_done']}/{m['pages_total']}"
            self.metric_placeholders[1].metric("Pages", pages_label)
            if m["chunks_total"] > 0:
                chunks_label = f"{m['chunks_done']}/{m['chunks_total']}"
            else:
                chunks_label = "—"
            self.metric_placeholders[2].metric("Chunks", chunks_label)
            self.metric_placeholders[3].metric("Elapsed", f"{elapsed:.0f}s")
        elif phase == "validate":
            self.metric_placeholders[0].metric("Records", m["records"])
            self.metric_placeholders[1].metric("Validation", "Running")
            self.metric_placeholders[2].metric("Elapsed", f"{elapsed:.0f}s")
            self.metric_placeholders[3].metric("Phase", "Validating")
        elif phase == "complete":
            self.metric_placeholders[0].metric("Total Records", m["records"])
            self.metric_placeholders[1].metric("Pages Scraped", m["pages_done"] or m["pages_total"])
            self.metric_placeholders[2].metric("Fields", m["fields"] or "—")
            self.metric_placeholders[3].metric("Total Time", f"{elapsed:.0f}s")

    def _update_phase(self, step):
        """Advance phase stepper based on current step."""
        new_phase = PHASE_MAP.get(step)
        if not new_phase or new_phase == self.current_phase:
            return False

        # Mark old phase complete, new phase active
        self.phase_status[self.current_phase] = "complete"
        self.phase_status[new_phase] = "active"
        self.current_phase = new_phase
        return True

    def _update_metrics(self, step, data):
        """Update metric counters from step data."""
        m = self.metrics

        if step in ("crawl_success", "crawl_complete"):
            if "words" in data:
                m["words"] = data["words"]
            if "layer" in data:
                m["layer"] = data["layer"]

        elif step == "layer_attempt":
            if "layer" in data:
                m["layer"] = data["layer"]

        elif step == "planning_complete":
            if "fields" in data:
                m["fields"] = len(data["fields"])
            if "pages" in data:
                m["pages_total"] = data["pages"]

        elif step == "multi_page_start":
            if "num_pages" in data:
                m["pages_total"] = data["num_pages"]

        elif step == "chunk_extracting":
            if "total" in data:
                m["chunks_total"] = data["total"]

        elif step in ("chunk_extracted", "extraction_batch_done"):
            if "records" in data:
                m["records"] = data["records"]
            m["chunks_done"] += 1

        elif step == "processing_page":
            if "page" in data:
                m["pages_done"] = data["page"] - 1
            if "total" in data:
                m["pages_total"] = data["total"]

        elif step == "page_extracted":
            m["pages_done"] = data.get("page", m["pages_done"] + 1)
            if "records" in data:
                m["records"] += data["records"]
            if "words" in data:
                m["words"] = data["words"]

        elif step == "extraction_complete":
            if "records" in data:
                m["records"] = data["records"]

    def update(self, step: str, data: dict = None):
        """Update progress with a new step."""
        with self._lock:
            elapsed = time.time() - self.start_time
            data = data or {}

            # Update phase and metrics
            phase_changed = self._update_phase(step)
            self._update_metrics(step, data)

            # Re-render zones
            if phase_changed:
                self._render_stepper()
            self._render_metrics()

            # Progress bar for chunk extraction
            m = self.metrics
            if self.current_phase == "extract" and m["chunks_total"] > 0:
                progress = min(m["chunks_done"] / m["chunks_total"], 1.0)
                self.progress_placeholder.progress(progress, text=f"Extracting chunk {m['chunks_done']}/{m['chunks_total']}")
            elif step in ("extraction_complete", "crew_complete", "complete"):
                self.progress_placeholder.empty()

            # Build log entry for Zone 3
            label = self.STEP_LABELS.get(step, step)
            icon = STEP_ICONS.get(step, "▸")

            detail_parts = []
            if "layer" in data:
                detail_parts.append(f"Layer {data['layer']}")
            if "words" in data:
                detail_parts.append(f"{data['words']} words")
            if "records" in data:
                detail_parts.append(f"{data['records']} records")
            if "page" in data:
                total = data.get("total", "?")
                detail_parts.append(f"Page {data['page']}/{total}")
            if "fields" in data:
                detail_parts.append(f"Fields: {', '.join(str(f) for f in data['fields'][:5])}")
            if "pages" in data:
                detail_parts.append(f"{data['pages']} pages")
            if "wait_seconds" in data:
                detail_parts.append(f"Waiting {data['wait_seconds']}s")
            if "chunk" in data:
                detail_parts.append(f"Chunk {data['chunk']}/{data.get('total', '?')}")
            if "boundaries" in data:
                detail_parts.append(f"{data['boundaries']} boundaries")
            if "elapsed_seconds" in data:
                detail_parts.append(f"{data['elapsed_seconds']}s elapsed")
            if "captcha_count" in data:
                detail_parts.append(f"CAPTCHA #{data['captcha_count']}")
            if "new_delay" in data:
                detail_parts.append(f"Delay now {data['new_delay']}s")
            if "chars" in data:
                detail_parts.append(f"{data['chars']} chars")
            if "file" in data:
                detail_parts.append(f"Saved to {data['file']}")
            if "error" in data:
                detail_parts.append(f"Error: {str(data['error'])[:80]}")
            if "message" in data:
                detail_parts.append(str(data["message"])[:100])

            detail = " | ".join(detail_parts) if detail_parts else ""
            entry = f"{icon} [{elapsed:.1f}s] {label}"
            if detail:
                entry += f" — {detail}"

            self.steps.append(entry)
            self.container.update(label=label)
            self.container.write(entry)

            # Mark complete or error
            if step in ("complete", "crew_complete"):
                self.phase_status["complete"] = "complete"
                self._render_stepper()
                self.container.update(label="Complete!", state="complete")
            elif step == "error":
                self.phase_status[self.current_phase] = "error"
                self._render_stepper()
                self.container.update(label="Error", state="error")

    def get_callback(self):
        """Return a callback function compatible with the pipeline."""
        def cb(step, data=None):
            self.update(step, data or {})
        return cb
