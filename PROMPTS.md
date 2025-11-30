# Prompt Engineering Documentation

This document explains the design rationale behind each agent's prompt template in the clinical summarization pipeline.

---

## Agent 0: Language Translator
### System Prompt
```
You are a professional medical translator. Convert the following text into clear, professional English.
Preserve all medical terminology, numbers, and proper nouns exactly. Do not summarize; provide a full translation.
```

### User Prompt Template
```
Translate this medical conversation from {source_language} to English.
Preserve all medical terms, dosages, and clinical details exactly.
Return ONLY the English translation (no commentary).

{text}
```

### Design Rationale
- **Preservation Focus:** Critical for medical accuracy; prevents loss of dosage/drug names.
- **No Commentary:** Ensures clean output for the next agent (Privacy Guard).

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
Your PRIORITY is ACCURACY and COMPLETENESS over conciseness.
You MUST include ALL medications (current and new), dosages, and diagnoses found in the data.
Omitting a medication or diagnosis is a CRITICAL ERROR.
Write a SOAP note using ONLY the information provided.
Distinguish clearly between patient reports and doctor orders.
```

### User Prompt Template
```
Create a SOAP note using ONLY the information below.
CRITICAL INSTRUCTION: You must list EVERY medication and diagnosis found in the data. Do not summarize lists - be exhaustive.
If the patient lists current meds, include them in Subjective.
If the doctor prescribes meds, include them in Plan.

Clinical Data:
{extracted_info}

Format:
**Subjective:** Patient's reported symptoms, history, CURRENT MEDICATIONS, and QUESTIONS/CONCERNS (use 'patient reports...')
**Objective:** Doctor's observations, vitals, and physical exam findings.
**Assessment:** All diagnoses mentioned (confirmed or suspected).
**Plan:** ALL treatments, new prescriptions, RECOMMENDATIONS, and follow-up instructions.

Review your output: Did you include every single medication name and dosage from the input? If not, fix it.
```

### Design Rationale
- **Priority Shift:** Explicitly prioritizes "Completeness" over "Conciseness" to pass safety validation.
- **Medication Safety:** Strict instruction to list ALL medications prevents critical omissions.
- **Section Clarity:** Explicitly maps "Current Meds" to Subjective and "Prescriptions/Recommendations" to Plan.
- **Questions/Concerns:** Added to Subjective to ensure patient queries are captured.
- **Validation Alignment:** Designed specifically to pass the strict safety checks of Agent 4.

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
- **Summarizer:** ROUGE-1: 0.149, ROUGE-L: 0.114
- **Validator:** 80% pass rate (strict mode working as intended)

---

## Future Improvements

1. **Dynamic Temperature:** Adjust based on task complexity
2. **Confidence Scores:** Ask LLM to rate its own certainty
3. **Multi-Model Validation:** Use different model for Agent 4 to catch model-specific biases
4. **Prompt Versioning:** Track prompt changes with A/B testing

---

**Last Updated:** November 30, 2025  
**Model:** Google Gemini 2.0 Flash Lite  
**Framework:** LangChain
