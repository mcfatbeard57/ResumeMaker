"""
Pydantic schemas for all structured LLM outputs.
"""
from pydantic import BaseModel, Field
from typing import Optional


class ResumeSection(BaseModel):
    """A single section of the resume (e.g., Professional Experience, Skills)."""
    section_name: str = Field(description="Name of the resume section")
    content: list[str] = Field(description="List of bullet points or lines in this section")


class ParsedResume(BaseModel):
    """Structured representation of the full resume."""
    name: str = Field(description="Candidate's full name")
    contact: str = Field(description="Contact information line")
    summary: str = Field(description="Professional summary paragraph")
    sections: list[ResumeSection] = Field(description="All resume sections with their content")


class GapAnalysis(BaseModel):
    """Gap analysis between resume and job description."""
    match_score: int = Field(ge=0, le=100, description="Overall JD match score (0-100)")
    missing_skills: list[str] = Field(description="Skills required by JD but missing from resume")
    weak_areas: list[str] = Field(description="Areas where resume is weak relative to JD emphasis")
    missing_keywords: list[str] = Field(description="Keywords from JD not present in resume")
    recommendations: list[str] = Field(description="Specific recommendations for improvement")


class WriterOutput(BaseModel):
    """Output from the Writer agent — optimized resume sections."""
    sections: list[ResumeSection] = Field(description="Rewritten resume sections")
    changes_summary: str = Field(description="Brief summary of what was changed and why")


class ReviewerOutput(BaseModel):
    """Output from the Reviewer agent — evaluation of the Writer's work."""
    score: int = Field(ge=0, le=100, description="JD alignment score (0-100)")
    approved: bool = Field(description="True if score >= threshold and no truthfulness issues")
    feedback: str = Field(description="Detailed feedback for the Writer if not approved")
    issues: list[str] = Field(default_factory=list, description="Specific issues found (e.g., fabrication, poor phrasing)")


class OptimizationState(BaseModel):
    """Full state object for the LangGraph optimization pipeline."""
    resume_path: str = Field(description="Path to the original resume PDF")
    resume_text: str = Field(default="", description="Raw extracted resume text")
    resume_sections: Optional[ParsedResume] = Field(default=None, description="Parsed resume structure")
    jd_text: str = Field(default="", description="Job description text")
    gap_analysis: Optional[GapAnalysis] = Field(default=None, description="Gap analysis result")
    current_draft: Optional[WriterOutput] = Field(default=None, description="Latest Writer output")
    reviewer_result: Optional[ReviewerOutput] = Field(default=None, description="Latest Reviewer output")
    iteration: int = Field(default=0, description="Current iteration number")
    history: list[dict] = Field(default_factory=list, description="History of all iterations")
    final_score: int = Field(default=0, description="Final match score")
    pdf_output_path: str = Field(default="", description="Path to generated output PDF")
    report_path: str = Field(default="", description="Path to generated gap report")
