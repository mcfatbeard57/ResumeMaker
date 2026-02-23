"""
Pipeline — LangGraph orchestration for the Resume-JD optimization flow.

Flow: parse_resume → parse_jd → gap_analysis → [writer ↔ reviewer loop] → generate_pdf → generate_report
"""
import os
import json
import time
from typing import TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from models.schemas import (
    ParsedResume, GapAnalysis, WriterOutput, ReviewerOutput,
    ResumeSection,
)
from utils.pdf_reader import extract_resume_text, extract_resume_sections
from utils.pdf_writer import generate_updated_resume
from utils.llm import get_parser_llm, load_config
from agents.writer import run_writer
from agents.reviewer import run_reviewer


# ── LangGraph State ──────────────────────────────────────────

class PipelineState(TypedDict):
    # Inputs
    resume_path: str
    jd_text: str
    config: dict
    
    # Parsed data
    resume_text: str
    resume_sections_raw: dict       # {section: [bullets]}
    resume_sections_str: str        # JSON string for prompts
    
    # Analysis
    gap_analysis: Optional[dict]
    gap_analysis_str: str
    
    # Agent loop
    current_draft: Optional[dict]
    reviewer_result: Optional[dict]
    reviewer_feedback: str
    iteration: int
    max_iterations: int
    approval_threshold: int
    history: list                    # [{iteration, score, approved, feedback}]
    
    # Outputs
    final_score: int
    pdf_output_path: str
    report_path: str
    report_content: str


# ── Node functions ───────────────────────────────────────────

def parse_resume(state: PipelineState) -> dict:
    """Node 1: Extract text and sections from the resume PDF."""
    print("📄 Parsing resume...")
    resume_path = state["resume_path"]
    
    resume_text = extract_resume_text(resume_path)
    sections = extract_resume_sections(resume_path)
    
    # Convert sections to a clean string for prompts
    sections_str = json.dumps(sections, indent=2, ensure_ascii=False)
    
    print(f"   Found {len(sections)} sections, {len(resume_text)} chars")
    return {
        "resume_text": resume_text,
        "resume_sections_raw": sections,
        "resume_sections_str": sections_str,
    }


def analyze_gaps(state: PipelineState) -> dict:
    """Node 2: Analyze gaps between resume and JD using LLM."""
    print("🔍 Analyzing resume-JD gaps...")
    config = state["config"]
    
    llm = get_parser_llm(config)
    system_prompt = config.get("prompts", {}).get("gap_analyzer", "Analyze gaps.")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt + """

You MUST respond with valid JSON matching this exact schema:
{{
    "match_score": <integer 0-100>,
    "missing_skills": ["skill1", "skill2"],
    "weak_areas": ["area1", "area2"],
    "missing_keywords": ["keyword1", "keyword2"],
    "recommendations": ["recommendation1", "recommendation2"]
}}

Return JSON only, no markdown fences."""),
        ("human", """## Resume:
{resume}

## Job Description:
{jd}

Analyze the alignment gaps. Return JSON only."""),
    ])
    
    parser = JsonOutputParser(pydantic_object=GapAnalysis)
    chain = prompt | llm | parser
    
    result = chain.invoke({
        "resume": state["resume_sections_str"],
        "jd": state["jd_text"],
    })
    
    gap = GapAnalysis(**result)
    gap_str = json.dumps(result, indent=2)
    
    print(f"   Initial match score: {gap.match_score}%")
    print(f"   Missing skills: {', '.join(gap.missing_skills[:5])}")
    
    return {
        "gap_analysis": result,
        "gap_analysis_str": gap_str,
        "iteration": 0,
        "reviewer_feedback": "No prior feedback — this is the first iteration.",
        "history": [],
    }


def run_writer_node(state: PipelineState) -> dict:
    """Node 3: Writer agent proposes resume edits."""
    iteration = state["iteration"] + 1
    print(f"\n✍️  Writer Agent — Iteration {iteration}...")
    
    config = state["config"]
    
    writer_output = run_writer(
        config=config,
        resume_sections=state["resume_sections_str"],
        jd_text=state["jd_text"],
        gap_analysis=state["gap_analysis_str"],
        reviewer_feedback=state["reviewer_feedback"],
    )
    
    print(f"   Changes: {writer_output.changes_summary[:100]}")
    
    return {
        "current_draft": writer_output.model_dump(),
        "iteration": iteration,
    }


def run_reviewer_node(state: PipelineState) -> dict:
    """Node 4: Reviewer agent evaluates the Writer's output."""
    iteration = state["iteration"]
    print(f"🔎 Reviewer Agent — Iteration {iteration}...")
    
    config = state["config"]
    draft = state["current_draft"]
    draft_str = json.dumps(draft, indent=2, ensure_ascii=False)
    
    reviewer_output = run_reviewer(
        config=config,
        original_resume=state["resume_text"],
        rewritten_sections=draft_str,
        jd_text=state["jd_text"],
    )
    
    # Record in history
    history_entry = {
        "iteration": iteration,
        "score": reviewer_output.score,
        "approved": reviewer_output.approved,
        "feedback": reviewer_output.feedback,
        "issues": reviewer_output.issues,
    }
    
    new_history = state.get("history", []) + [history_entry]
    
    print(f"   Score: {reviewer_output.score}% | Approved: {reviewer_output.approved}")
    if not reviewer_output.approved:
        print(f"   Feedback: {reviewer_output.feedback[:100]}...")
    
    return {
        "reviewer_result": reviewer_output.model_dump(),
        "reviewer_feedback": reviewer_output.feedback,
        "final_score": reviewer_output.score,
        "history": new_history,
    }


def generate_pdf_node(state: PipelineState) -> dict:
    """Node 5: Generate the updated resume PDF."""
    print("\n📝 Generating updated PDF...")
    
    config = state["config"]
    output_dir = config.get("pdf", {}).get("output_dir", "output")
    output_path = os.path.join(output_dir, "optimized_resume.pdf")
    
    # Convert writer output sections to the format pdf_writer expects
    draft = state["current_draft"]
    updated_sections = {}
    for section in draft.get("sections", []):
        section_name = section["section_name"]
        updated_sections[section_name] = section["content"]
    
    pdf_path = generate_updated_resume(
        original_path=state["resume_path"],
        updated_sections=updated_sections,
        output_path=output_path,
    )
    
    return {"pdf_output_path": pdf_path}


def generate_report_node(state: PipelineState) -> dict:
    """Node 6: Generate the gap analysis report as markdown."""
    print("📊 Generating gap analysis report...")
    
    config = state["config"]
    output_dir = config.get("pdf", {}).get("output_dir", "output")
    report_path = os.path.join(output_dir, "gap_report.md")
    os.makedirs(output_dir, exist_ok=True)
    
    gap = state.get("gap_analysis", {})
    history = state.get("history", [])
    draft = state.get("current_draft", {})
    
    # Build report markdown
    lines = [
        "# Resume-JD Gap Analysis Report",
        "",
        "## Score Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Initial Match Score | {gap.get('match_score', 'N/A')}% |",
        f"| Final Match Score | {state.get('final_score', 'N/A')}% |",
        f"| Iterations | {state.get('iteration', 0)} |",
        f"| Approved | {history[-1]['approved'] if history else 'N/A'} |",
        "",
        "## Missing Skills",
        "",
    ]
    
    for skill in gap.get("missing_skills", []):
        lines.append(f"- {skill}")
    
    lines.extend([
        "",
        "## Weak Areas",
        "",
    ])
    for area in gap.get("weak_areas", []):
        lines.append(f"- {area}")
    
    lines.extend([
        "",
        "## Missing Keywords",
        "",
    ])
    for kw in gap.get("missing_keywords", []):
        lines.append(f"- `{kw}`")
    
    lines.extend([
        "",
        "## Recommendations",
        "",
    ])
    for rec in gap.get("recommendations", []):
        lines.append(f"- {rec}")
    
    lines.extend([
        "",
        "## Optimization History",
        "",
        "| Iteration | Score | Approved | Key Feedback |",
        "|-----------|-------|----------|-------------|",
    ])
    for entry in history:
        fb = entry.get("feedback", "")[:80].replace("|", "/")
        lines.append(
            f"| {entry['iteration']} | {entry['score']}% | "
            f"{'✅' if entry['approved'] else '❌'} | {fb} |"
        )
    
    lines.extend([
        "",
        "## Changes Applied",
        "",
    ])
    for section in draft.get("sections", []):
        lines.append(f"### {section['section_name']}")
        lines.append("")
        for bullet in section.get("content", []):
            lines.append(f"- {bullet}")
        lines.append("")
    
    lines.extend([
        "",
        f"*Changes summary: {draft.get('changes_summary', 'N/A')}*",
        "",
        "---",
        f"*Generated by Resume-JD Optimizer*",
    ])
    
    report_content = "\n".join(lines)
    
    with open(report_path, "w") as f:
        f.write(report_content)
    
    print(f"   Report saved to: {report_path}")
    
    return {
        "report_path": report_path,
        "report_content": report_content,
    }


# ── Conditional edge ─────────────────────────────────────────

def should_continue(state: PipelineState) -> str:
    """Decide whether to loop back to writer or proceed to PDF generation."""
    reviewer = state.get("reviewer_result", {})
    iteration = state.get("iteration", 0)
    max_iter = state.get("max_iterations", 5)
    threshold = state.get("approval_threshold", 90)
    
    score = reviewer.get("score", 0)
    approved = reviewer.get("approved", False)
    
    if approved or score >= threshold:
        print(f"\n✅ Approved! Score: {score}% (threshold: {threshold}%)")
        return "generate_pdf"
    
    if iteration >= max_iter:
        print(f"\n⚠️  Max iterations ({max_iter}) reached. Score: {score}%")
        return "generate_pdf"
    
    print(f"   ↻ Looping back to Writer (score {score}% < {threshold}%)")
    return "writer"


# ── Build the graph ──────────────────────────────────────────

def build_graph() -> StateGraph:
    """Build the LangGraph state machine for the optimization pipeline."""
    graph = StateGraph(PipelineState)
    
    # Add nodes
    graph.add_node("parse_resume", parse_resume)
    graph.add_node("analyze_gaps", analyze_gaps)
    graph.add_node("writer", run_writer_node)
    graph.add_node("reviewer", run_reviewer_node)
    graph.add_node("generate_pdf", generate_pdf_node)
    graph.add_node("generate_report", generate_report_node)
    
    # Add edges
    graph.set_entry_point("parse_resume")
    graph.add_edge("parse_resume", "analyze_gaps")
    graph.add_edge("analyze_gaps", "writer")
    graph.add_edge("writer", "reviewer")
    
    # Conditional: reviewer → writer OR generate_pdf
    graph.add_conditional_edges(
        "reviewer",
        should_continue,
        {
            "writer": "writer",
            "generate_pdf": "generate_pdf",
        }
    )
    
    graph.add_edge("generate_pdf", "generate_report")
    graph.add_edge("generate_report", END)
    
    return graph


def run_optimization(
    resume_path: str,
    jd_text: str,
    config: dict,
) -> dict:
    """
    Main entry point: run the full optimization pipeline.
    
    Args:
        resume_path: Path to the resume PDF
        jd_text: Job description text
        config: Loaded config dict
    
    Returns:
        dict with pdf_path, report_path, final_score, history, report_content
    """
    agent_config = config.get("agent", {})
    
    # Initial state
    initial_state: PipelineState = {
        "resume_path": resume_path,
        "jd_text": jd_text,
        "config": config,
        "resume_text": "",
        "resume_sections_raw": {},
        "resume_sections_str": "",
        "gap_analysis": None,
        "gap_analysis_str": "",
        "current_draft": None,
        "reviewer_result": None,
        "reviewer_feedback": "",
        "iteration": 0,
        "max_iterations": agent_config.get("max_iterations", 5),
        "approval_threshold": agent_config.get("approval_threshold", 90),
        "history": [],
        "final_score": 0,
        "pdf_output_path": "",
        "report_path": "",
        "report_content": "",
    }
    
    # Build and compile graph
    graph = build_graph()
    app = graph.compile()
    
    print("🚀 Starting Resume-JD Optimization Pipeline")
    print(f"   Models: Writer={config['llm']['writer_model']}, Reviewer={config['llm']['reviewer_model']}")
    print(f"   Max iterations: {agent_config.get('max_iterations', 5)}")
    print(f"   Approval threshold: {agent_config.get('approval_threshold', 90)}%")
    print("=" * 60)
    
    start_time = time.time()
    
    # Run the graph
    final_state = None
    for step in app.stream(initial_state):
        # step is {node_name: updated_state_dict}
        for node_name, node_output in step.items():
            final_state = {**initial_state, **(final_state or {}), **node_output}
    
    elapsed = time.time() - start_time
    
    print("=" * 60)
    print(f"🏁 Pipeline complete in {elapsed:.1f}s")
    print(f"   Final score: {final_state.get('final_score', 'N/A')}%")
    print(f"   PDF: {final_state.get('pdf_output_path', 'N/A')}")
    print(f"   Report: {final_state.get('report_path', 'N/A')}")
    
    return {
        "pdf_path": final_state.get("pdf_output_path", ""),
        "report_path": final_state.get("report_path", ""),
        "final_score": final_state.get("final_score", 0),
        "history": final_state.get("history", []),
        "report_content": final_state.get("report_content", ""),
        "gap_analysis": final_state.get("gap_analysis", {}),
        "elapsed_seconds": elapsed,
    }


# ── CLI support ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python pipeline.py <resume.pdf> --jd 'Job description text'")
        sys.exit(1)
    
    resume_path = sys.argv[1]
    jd_text = " ".join(sys.argv[3:]) if "--jd" in sys.argv else sys.argv[2]
    
    config = load_config()
    result = run_optimization(resume_path, jd_text, config)
    
    print(f"\nResult: {json.dumps({k: v for k, v in result.items() if k != 'report_content'}, indent=2)}")
