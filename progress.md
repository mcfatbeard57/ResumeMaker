# 📋 Progress & Roadmap

## ✅ Completed — v1.0 (2026-02-23)

### Core Pipeline
- [x] PDF resume parsing via PyMuPDF (text, positions, sections)
- [x] LLM-based gap analysis (resume ↔ JD comparison)
- [x] Writer agent (qwen2.5:7b) — rewrites bullets to align with JD
- [x] Reviewer agent (llama3.1:8b) — scores & validates truthfulness
- [x] LangGraph state machine with conditional Writer↔Reviewer loop
- [x] Pydantic-validated structured outputs for all LLM calls

### PDF Generation
- [x] Overlay-based layout-preserving PDF editing (redact + insert)
- [x] Font/position/color matching from original document
- [x] Unicode sanitization for LLM-generated text

### Reports & Observability
- [x] Gap analysis report (in-notebook + markdown file)
- [x] Iteration history with score progression
- [x] LangSmith integration (ready — needs API key)

### Interface
- [x] Jupyter notebook with 7-cell workflow
- [x] CLI support via `pipeline.py`

---

## 🔜 Planned — v1.1

- [ ] Multi-page resume support (currently optimized for single-page)
- [ ] Section-level diff view (before → after per bullet point)
- [ ] Token usage & latency metrics in gap report
- [ ] Support for additional models (Gemma 2, Mistral, etc.)
- [ ] Batch mode — optimize against multiple JDs at once

## 🔮 Future Ideas — v2.0

- [ ] Visual PDF diff (side-by-side original vs optimized)
- [ ] ATS keyword scanner (parse ATS-specific requirements)
- [ ] Cover letter generation aligned to the same JD
- [ ] Resume template library (generate fresh layouts)
- [ ] LangSmith dashboard with token cost tracking
- [ ] Auto-detect resume sections (remove font-heuristic dependency)
- [ ] Gradio / Streamlit web UI (if needed beyond notebook)
- [ ] Fine-tune a small model specifically for resume optimization
- [ ] Integration with job boards (LinkedIn, Indeed) for JD fetching

---

## 🐛 Known Limitations

- **Single-page resumes only** — multi-page overlay not yet implemented
- **Font matching** — uses Helvetica as fallback; may not perfectly match custom fonts
- **Text overflow** — if optimized bullet is significantly longer than original, font size is reduced by 0.5pt
- **LangSmith** — disabled by default (requires API key from smith.langchain.com)
- **Section detection** — relies on Arial-Black font heuristic; may need adjustment for different resume templates

---

## 📝 Changelog

### v1.0 — 2026-02-23
- Initial release
- Full pipeline: parse → gap analysis → writer↔reviewer loop → PDF + report
- Dual model: qwen2.5:7b (writer) + llama3.1:8b (reviewer)
- Overlay-based layout-preserving PDF editing
- Jupyter notebook interface
- Benchmark: 80% → 95% score in 1 iteration (~108s)
