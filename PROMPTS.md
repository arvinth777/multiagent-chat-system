# Prompt Engineering Documentation

This document explains the design rationale behind each agent's prompt template in the clinical summarization pipeline.

---

## Agent 1: Privacy Guard

### System Prompt
```
You are a HIPAA compliance expert specializing in medical data anonymization.
Your task is to remove all Personally Identifiable Information (PII) from medical conversations.
```

### User Prompt Template
```
Anonymize the following medical conversation by replacing PII with placeholders:
- Patient names → [PATIENT_NAME]
- Doctor names → [DOCTOR_NAME]  
- Dates → [DATE]
- Locations → [LOCATION]
- Contact info → [CONTACT_INFO]

Return ONLY the anonymized text, preserving all clinical information.

Text: {raw_text}
```

### Design Rationale
- **Temperature: 0.0** - Deterministic output for compliance
- **Why this works:** Explicit placeholder format ensures consistency. The instruction to "preserve all clinical information" prevents over-redaction.
- **Fallback:** Regex patterns for common PII (phone, email, dates) as safety net

---

## Agent 2: Clinical Extractor

### System Prompt
```
You are a clinical information extraction specialist.
Extract structured medical entities from conversations and return valid JSON.
```

### User Prompt Template
```
Extract clinical information from this anonymized conversation.

Return a JSON object with this exact schema:
{
  "chief_complaint": "string",
  "symptoms": ["list of symptoms"],
  "medications": [{"name": "str", "dosage": "str", "frequency": "str"}],
  "diagnoses": ["list of diagnoses"],
  "vitals": {"BP": "str", "HR": "str", "Temp": "str"}
}

Conversation: {anonymized_text}
```

### Design Rationale
- **Temperature: 0.0** - Structured output requires determinism
- **Why JSON schema:** Forces consistent output format, enables downstream validation
- **Retry logic:** If JSON parsing fails, sends repair prompt with error details
- **Max tokens: 800** - Sufficient for typical clinical data, prevents runaway generation

---

## Agent 3: SOAP Summarizer

### System Prompt
```
You are a senior physician assistant creating clinical documentation.
Write concise, professional SOAP notes from structured clinical data.
```

### User Prompt Template
```
Create a SOAP note (Subjective, Objective, Assessment, Plan) from this clinical data:

{extracted_info}

Format:
**SOAP Note**

**Subjective:**
[Patient's reported symptoms and concerns]

**Objective:**
[Measurable findings, vitals, exam results]

**Assessment:**
[Clinical diagnosis and reasoning]

**Plan:**
[Treatment plan, medications, follow-up]

Keep it concise and professional.
```

### Design Rationale
- **Temperature: 0.0** - Medical documentation must be consistent
- **Why SOAP format:** Industry-standard clinical note structure
- **Input:** Uses structured JSON from Agent 2, not raw text - reduces hallucination risk
- **Conciseness instruction:** Prevents verbose summaries that lose focus

---

## Agent 4: Clinical Validator

### System Prompt
```
You are a Clinical Safety Auditor.
Compare AI-generated summaries against source text to detect errors.
```

### User Prompt Template
```
Compare the AI summary against the original conversation.

Original: {source_text}

Summary: {summary}

Return JSON:
{
  "status": "PASS" or "FAIL",
  "issues": ["list of problems"],
  "missing_info": ["critical omissions"],
  "hallucinations": ["fabricated information"]
}

Be strict. Flag any discrepancies.
```

### Design Rationale
- **Temperature: 0.0** - Safety checks must be deterministic
- **Why "Be strict":** Better to over-flag than miss errors in healthcare
- **Structured output:** JSON enables programmatic handling of validation results
- **Three categories:** Separates general issues, omissions, and hallucinations for clarity

---

## Cross-Agent Design Principles

### 1. **Progressive Refinement**
Each agent builds on the previous:
- Agent 1: Raw → Anonymized
- Agent 2: Anonymized → Structured
- Agent 3: Structured → Summary
- Agent 4: Summary + Source → Validation

This reduces error propagation compared to single-shot summarization.

### 2. **Temperature = 0.0 Throughout**
Medical AI requires **reproducibility**. Same input should yield same output for:
- Regulatory compliance
- Debugging
- Trust building

### 3. **Explicit Output Formats**
Every prompt specifies exact output format (JSON schema, SOAP structure, placeholders). This:
- Enables validation
- Reduces parsing errors
- Makes failures obvious

### 4. **Safety-First Language**
- "Be strict" (Validator)
- "Preserve all clinical information" (Privacy)
- "Valid JSON" (Extractor)

These phrases bias the LLM toward conservative, safe outputs.

---

## Prompt Evolution Notes

### What We Tried and Discarded

1. **Chain-of-Thought for Extractor**
   - **Tried:** "Explain your reasoning before extracting"
   - **Result:** Verbose, inconsistent JSON
   - **Lesson:** CoT works for reasoning tasks, not structured extraction

2. **Few-Shot Examples**
   - **Tried:** Including 2-3 example conversations
   - **Result:** Minimal improvement, wasted tokens
   - **Lesson:** Schema + clear instructions > examples for this task

3. **Higher Temperature for Summarizer**
   - **Tried:** Temperature 0.3 for "natural" summaries
   - **Result:** Inconsistent formatting, occasional hallucinations
   - **Lesson:** Medical docs need determinism over creativity

---

## Metrics

From batch processing (5 samples):
- **Privacy Agent:** 100% PII redaction (verified manually)
- **Extractor:** 100% valid JSON (after retry logic)
- **Summarizer:** ROUGE-1: 0.220, ROUGE-L: 0.127
- **Validator:** 60% pass rate (strict mode working as intended)

---

## Future Improvements

1. **Dynamic Temperature:** Adjust based on task complexity
2. **Confidence Scores:** Ask LLM to rate its own certainty
3. **Multi-Model Validation:** Use different model for Agent 4 to catch model-specific biases
4. **Prompt Versioning:** Track prompt changes with A/B testing

---

**Last Updated:** November 30, 2024  
**Model:** Google Gemini 2.0 Flash Lite  
**Framework:** LangChain
