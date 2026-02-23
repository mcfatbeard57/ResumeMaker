"""
Writer Agent — Proposes optimized resume content using qwen2.5:7b.
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from models.schemas import WriterOutput, ResumeSection
from utils.llm import get_writer_llm


def create_writer_chain(config: dict):
    """
    Create the Writer agent chain.
    Returns a LangChain Runnable: prompt | llm | parser
    """
    llm = get_writer_llm(config)
    
    system_prompt = config.get("prompts", {}).get("writer", "You are a resume writer.")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt + """

You MUST respond with valid JSON matching this exact schema:
{{
    "sections": [
        {{
            "section_name": "Section Name",
            "content": ["bullet point 1", "bullet point 2"]
        }}
    ],
    "changes_summary": "Brief description of changes made"
}}

CRITICAL RULES:
- Each bullet point MUST start with '•' followed by a space
- Keep each bullet point under 200 characters
- Do NOT add new bullet points — only modify existing ones
- Preserve the exact number of bullets per section
- Do NOT invent any experience, metric, or credential
"""),
        ("human", """## Original Resume Sections:
{resume_sections}

## Job Description:
{jd_text}

## Gap Analysis:
{gap_analysis}

## Reviewer Feedback (if any):
{reviewer_feedback}

Rewrite the resume sections to better align with the job description.
Only modify sections that are relevant to the gaps identified.
Return JSON only, no markdown fences."""),
    ])
    
    parser = JsonOutputParser(pydantic_object=WriterOutput)
    
    chain = prompt | llm | parser
    return chain


def run_writer(
    config: dict,
    resume_sections: str,
    jd_text: str,
    gap_analysis: str,
    reviewer_feedback: str = "No prior feedback — this is the first iteration.",
) -> WriterOutput:
    """
    Run the Writer agent to produce optimized resume sections.
    
    Returns WriterOutput with sections and changes_summary.
    """
    chain = create_writer_chain(config)
    
    result = chain.invoke({
        "resume_sections": resume_sections,
        "jd_text": jd_text,
        "gap_analysis": gap_analysis,
        "reviewer_feedback": reviewer_feedback,
    })
    
    # Parse into Pydantic model
    if isinstance(result, dict):
        # Ensure sections have proper structure
        sections = []
        for s in result.get("sections", []):
            sections.append(ResumeSection(
                section_name=s.get("section_name", ""),
                content=s.get("content", [])
            ))
        return WriterOutput(
            sections=sections,
            changes_summary=result.get("changes_summary", "")
        )
    
    return result
