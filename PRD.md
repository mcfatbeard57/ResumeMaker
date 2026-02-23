# **PRD — Resume ↔ JD Gap Analyzer & Optimizer**

## **1. Product Definition**

**Product Name:** Resume-JD Optimizer
**Type:** Local Jupyter Notebook Application
**Execution Mode:** Event-Driven (JD → Output PDF)
**Primary Objective:**
Analyze a resume (PDF) against a Job Description (JD), identify alignment gaps, iteratively optimize resume content via LLM agents, and generate an updated PDF **without altering formatting, fonts, or layout**.

---

## **2. Goals**

1. Accept resume PDF as input (one-time ingestion)
2. Parse and semantically understand resume content
3. Accept JD as user input (event trigger)
4. Identify:

   * Missing skills
   * Weak alignment areas
   * Missing keywords
5. Iteratively refine resume using multi-agent loop
6. Achieve ≥ **90% JD Match Score**
7. Generate:

   * Updated Resume PDF (layout preserved)
   * Gap Analysis Report
   * Observability & token metrics

---

## **3. Non-Goals**

* No UI beyond Jupyter Notebook
* No remote/cloud LLM calls
* No layout redesign
* No fabrication of experience or credentials

---

## **4. System Inputs**

### **4.1 Resume Input**

**Type:** PDF
**Characteristics:**

* Static structure
* Known formatting
* One-time ingestion

**Assumption:** Resume layout must remain unchanged.

---

### **4.2 Job Description (Event Trigger)**

**Type:** Raw text (user pasted)
**Characteristics:**

* Variable length
* Unstructured
* Drives optimization pipeline

---

## **5. System Outputs**

1. **Updated Resume PDF**

   * Same fonts
   * Same layout
   * Only approved textual edits

2. **Gap Analysis Report**

   * Initial score
   * Final score
   * Missing skills/keywords
   * Edits applied

3. **Observability Metrics**

   * LLM calls
   * Token usage
   * Latency
   * Iteration trace

---

## **6. Functional Requirements**

### **FR-1 Resume Parsing**

* Extract raw text from PDF
* Preserve structural sections
* Generate structured internal representation

---

### **FR-2 Semantic Understanding**

* Use Ollama LLM to interpret resume meaning
* Identify skills, experience, tools, domains

---

### **FR-3 JD Parsing**

* Extract:

  * Skills
  * Responsibilities
  * Keywords
  * Seniority signals

---

### **FR-4 Gap Analysis**

* Compare resume ↔ JD
* Compute Match Score
* Identify missing / weak areas

---

### **FR-5 Multi-Agent Optimization Loop**

#### **Writer Agent**

**Role:** Propose resume edits
**Constraints:**

* Only modify relevant content
* No hallucinated claims
* No formatting instructions

---

#### **Reviewer Agent**

**Role:** Validate Writer edits
**Checks:**

* Truthfulness
* JD relevance
* Score improvement
* Constraint compliance

---

#### **Loop Termination Conditions**

* Score ≥ 90%
* Max iterations reached

---

### **FR-6 Resume Update Engine**

* Apply approved edits only
* Preserve layout & typography

---

### **FR-7 PDF Generation**

* Output visually identical document
* Only textual differences allowed

---

### **FR-8 Observability & Tracing**

* Trace all LLM interactions
* Log prompts/responses
* Capture token usage
* Track iteration flow

---

## **7. Constraints**

| Constraint          | Requirement |
| ------------------- | ----------- |
| Layout Preservation | Mandatory   |
| Font Preservation   | Mandatory   |
| Truthfulness        | Mandatory   |
| Local Execution     | Mandatory   |
| Structured Outputs  | Mandatory   |

---

## **8. Success Criteria**

1. JD Match Score ≥ 90%
2. No fabricated experience
3. No layout drift
4. All LLM outputs validated
5. Observability logs complete

---

## **9. Assumptions**

1. Resume PDF has stable formatting
2. Text extraction is reliable
3. Ollama model available locally
4. Global venv pre-configured
5. JD provided as raw text

---

## **10. Risks & Mitigations**

| Risk                 | Mitigation                      |
| -------------------- | ------------------------------- |
| LLM hallucination    | Reviewer Agent + strict prompts |
| Layout corruption    | Coordinate-based PDF editing    |
| Unstructured outputs | Pydantic validation             |
| Infinite loop        | Max iteration cap               |

---

## **11. Technology Stack**

| Layer             | Tool / Framework      |
| ----------------- | --------------------- |
| Environment       | Global venv           |
| Interface         | Jupyter Notebook      |
| LLM Runtime       | Ollama (local)        |
| Orchestration     | LangChain             |
| Agents            | LangChain-based roles |
| Schema Validation | Pydantic              |
| PDF Parsing       | PyMuPDF / pdfplumber  |
| PDF Generation    | reportlab / overlay   |
| Observability     | Langtrace             |

---

## **12. Observability Requirements**

Langtrace must capture:

* LLM calls
* Prompts & responses
* Token usage
* Latency
* Agent iteration flow
* Errors / retries

---

## **13. System Rules**

1. Never invent experience or credentials
2. Never alter formatting/layout/fonts
3. Only apply Reviewer-approved edits
4. All LLM outputs must be structured
5. Terminate loop deterministically

---

## **14. Execution Flow**

Resume PDF (one-time) → Parse → Semantic Model
JD Input (event) → Parse → Gap Analysis
Gap Analysis → Writer Agent → Reviewer Agent → Loop
Approved Edits → Apply → PDF Generation
All Steps → Langtrace Logging → Metrics Output

---

## **15. Exit Conditions**

Pipeline completes when:

* Match Score ≥ 90%
  OR
* Max Iterations Reached

---

## **16. Deliverables**

1. Updated Resume PDF
2. Optimization Report
3. Observability / Token Metrics

---

**End of Document **
