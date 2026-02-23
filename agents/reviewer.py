"""
Reviewer Agent — Evaluates Writer output using llama3.1:8b.
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from models.schemas import ReviewerOutput
from utils.llm import get_reviewer_llm


def create_reviewer_chain(config: dict):
    """
    Create the Reviewer agent chain.
    Returns a LangChain Runnable: prompt | llm | parser
    """
    llm = get_reviewer_llm(config)
    
    system_prompt = config.get("prompts", {}).get("reviewer", "You are a resume reviewer.")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt + """

You MUST respond with valid JSON matching this exact schema:
{{
    "score": <integer 0-100>,
    "approved": <true or false>,
    "feedback": "Detailed feedback string",
    "issues": ["issue 1", "issue 2"]
}}

SCORING GUIDE:
- 90-100: Excellent alignment, ready for submission
- 75-89: Good alignment, minor improvements needed
- 60-74: Moderate alignment, significant gaps remain
- Below 60: Poor alignment, major rewrites needed

Set approved=true ONLY if score >= 90 AND there are zero truthfulness issues.
"""),
        ("human", """## Original Resume:
{original_resume}

## Rewritten Resume Sections:
{rewritten_sections}

## Job Description:
{jd_text}

Evaluate the rewritten resume sections against the original and the JD.
Check for truthfulness, keyword coverage, readability, and alignment.
Return JSON only, no markdown fences."""),
    ])
    
    parser = JsonOutputParser(pydantic_object=ReviewerOutput)
    
    chain = prompt | llm | parser
    return chain


def run_reviewer(
    config: dict,
    original_resume: str,
    rewritten_sections: str,
    jd_text: str,
) -> ReviewerOutput:
    """
    Run the Reviewer agent to evaluate the Writer's output.
    
    Returns ReviewerOutput with score, approved, feedback, issues.
    """
    chain = create_reviewer_chain(config)
    
    result = chain.invoke({
        "original_resume": original_resume,
        "rewritten_sections": rewritten_sections,
        "jd_text": jd_text,
    })
    
    # Parse into Pydantic model
    if isinstance(result, dict):
        return ReviewerOutput(
            score=result.get("score", 0),
            approved=result.get("approved", False),
            feedback=result.get("feedback", ""),
            issues=result.get("issues", []),
        )
    
    return result
