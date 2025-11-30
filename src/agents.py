# src/agents.py
"""
Robust agent wrappers for the pipeline:
- PrivacyGuard
- ClinicalExtractor
- Summarizer
- Validator

These classes use the call_llm adapter in src.utils to perform LLM calls.
They include safe parsing, retries, and deterministic settings for structured outputs.
"""

import json
import time
import logging
from typing import Any, Dict, Optional

from src.utils import call_llm, emergency_pii_removal, append_jsonl

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# -------------------------
# Helpers
# -------------------------
def safe_json_loads(s: str) -> Optional[dict]:
    """Try to parse JSON robustly; return dict or None."""
    try:
        return json.loads(s)
    except Exception:
        # heuristic: strip fences and try again
        s2 = s.strip()
        if s2.startswith("```"):
            # remove starting fence
            parts = s2.split("```")
            # find the part that looks like json
            for p in parts:
                p = p.strip()
                if p.startswith("{") and p.endswith("}"):
                    try:
                        return json.loads(p)
                    except Exception:
                        continue
        # last resort: try to find first {...} block
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            cand = s[start:end+1]
            try:
                return json.loads(cand)
            except Exception:
                return None
        return None


def _llm_call_with_logging(prompt: str, system: str, temperature: float = 0.0, max_tokens: int = 800):
    """Call call_llm and append a small JSONL log for auditability."""
    t0 = time.time()
    resp = call_llm(prompt=prompt, system_message=system, temperature=temperature, max_tokens=max_tokens)
    meta = {
        "timestamp": time.time(),
        "system_preview": system[:300],
        "prompt_preview": prompt[:800],
        "response_preview": (resp or "")[:800],
        "elapsed": round(time.time() - t0, 3)
    }
    append_jsonl("logs/llm_calls.jsonl", meta)
    return resp


# -------------------------
# Agent 0: LanguageTranslator
# -------------------------
class LanguageTranslator:
    SYSTEM = (
        "You are a professional medical translator. Convert the following text into clear, professional English. "
        "Preserve all medical terminology, numbers, and proper nouns exactly. Do not summarize; provide a full translation."
    )

    def __init__(self, max_tokens: int = 1200):
        self.max_tokens = max_tokens

    def run(self, text: str, source_language: str = "auto") -> Dict[str, Any]:
        """
        Translate medical conversation to English.
        Returns dict: {'translated_text': str, 'source_language': str, 'ok': bool}
        """
        prompt = (
            f"Translate this medical conversation from {source_language} to English. "
            f"Preserve all medical terms, dosages, and clinical details exactly. "
            f"Return ONLY the English translation (no commentary).\n\n{text}"
        )
        try:
            resp = _llm_call_with_logging(
                prompt=prompt,
                system=self.SYSTEM,
                temperature=0.0,
                max_tokens=self.max_tokens
            )
            if not resp or len(resp.strip()) < 20:
                raise ValueError("Translation failed or too short")
            return {
                "translated_text": resp.strip(),
                "source_language": source_language,
                "ok": True
            }
        except Exception as e:
            logger.exception("LanguageTranslator failed")
            return {
                "translated_text": text,  # Fallback to original
                "source_language": source_language,
                "ok": False,
                "error": str(e)
            }


# -------------------------
# Agent: PrivacyGuard
# -------------------------
class PrivacyGuard:
    SYSTEM = (
        "You are a HIPAA compliance expert. Remove all personal identifiable information (PII) "
        "from the medical text while preserving clinical content (symptoms, meds, diagnoses, vitals). "
        "Replace names with [PATIENT_NAME] or [DOCTOR_NAME], dates with [DATE], locations with [LOCATION], "
        "phone / contact with [CONTACT_INFO], emails with [EMAIL]. Return ONLY the anonymized text (no commentary)."
    )

    def __init__(self, max_tokens: int = 800):
        self.max_tokens = max_tokens

    def run(self, text: str) -> Dict[str, Any]:
        """Return dict: {'anonymized_text': str, 'used_fallback': bool, 'note': str}"""
        prompt = f"Anonymize the following conversation and return ONLY the anonymized conversation:\n\n{text}"
        try:
            resp = _llm_call_with_logging(prompt=prompt, system=self.SYSTEM, temperature=0.0, max_tokens=self.max_tokens)
            # sanity checks: must be reasonably long and not identical to input
            if not resp or len(resp.strip()) < 20 or resp.strip() == text.strip():
                raise ValueError("LLM anonymization failed or suspicious")
            return {"anonymized_text": resp.strip(), "used_fallback": False, "note": "LLM anonymization successful"}
        except Exception as e:
            logger.warning("PrivacyGuard LLM failed, using regex fallback: %s", e)
            fallback = emergency_pii_removal(text)
            append_jsonl("logs/privacy_fallback.jsonl", {"timestamp": time.time(), "note": str(e)})
            return {"anonymized_text": fallback, "used_fallback": True, "note": f"Fallback used: {e}"}


# -------------------------
# Agent: ClinicalExtractor
# -------------------------
class ClinicalExtractor:
    SYSTEM = (
        "You are a clinical information extractor. Extract structured fields from the anonymized conversation. "
        "Return ONLY a JSON object with these keys:\n"
        "  - chief_complaint (string)\n"
        "  - symptoms (list of strings)\n"
        "  - medications (list of {name, dosage, frequency} objects)\n"
        "  - diagnoses (list of strings)\n"
        "  - vitals (object, e.g. {BP: '120/80', HR: '80', Temp: '98.6F'})\n"
        "If a field is not present, return empty string or empty list/object accordingly."
    )

    JSON_EXAMPLE = json.dumps({
        "chief_complaint": "Headache",
        "symptoms": ["headache", "nausea"],
        "medications": [{"name": "ibuprofen", "dosage": "400mg", "frequency": "twice daily"}],
        "diagnoses": ["tension headache"],
        "vitals": {"BP": "", "HR": "", "Temp": ""}
    }, indent=2)

    def __init__(self, max_tokens: int = 800, tries: int = 2):
        self.max_tokens = max_tokens
        self.tries = tries

    def run(self, anonymized_text: str) -> Dict[str, Any]:
        prompt = (
            "Extract clinical data from the anonymized conversation below. "
            "Return ONLY valid JSON (no extra text). Example of expected JSON:\n\n"
            f"{self.JSON_EXAMPLE}\n\n"
            f"Conversation:\n{anonymized_text}"
        )

        last_err = None
        for attempt in range(self.tries):
            try:
                resp = _llm_call_with_logging(prompt=prompt, system=self.SYSTEM, temperature=0.0, max_tokens=self.max_tokens)
                parsed = safe_json_loads(resp or "")
                if parsed and isinstance(parsed, dict):
                    return {"clinical_data": parsed, "raw_output": resp, "parse_ok": True}
                last_err = f"Invalid JSON on attempt {attempt+1}"
                # fallthrough to repair
                repair_prompt = (
                    "Your previous output was not valid JSON. Please return only valid JSON matching this schema: "
                    "chief_complaint (string), symptoms (list), medications (list of objects with name/dosage/frequency), "
                    "diagnoses (list), vitals (object). Return JSON only."
                )
                resp2 = _llm_call_with_logging(prompt=repair_prompt + "\n\nPrevious output:\n" + (resp or ""), system=self.SYSTEM, temperature=0.0, max_tokens=400)
                parsed2 = safe_json_loads(resp2 or "")
                if parsed2 and isinstance(parsed2, dict):
                    return {"clinical_data": parsed2, "raw_output": resp2, "parse_ok": True, "repaired": True}
            except Exception as e:
                last_err = str(e)
                logger.exception("ClinicalExtractor error")
                time.sleep(0.5)
        # final fallback: empty structure
        empty = {
            "chief_complaint": "",
            "symptoms": [],
            "medications": [],
            "diagnoses": [],
            "vitals": {}
        }
        return {"clinical_data": empty, "raw_output": None, "parse_ok": False, "error": last_err}


# -------------------------
# Agent: Summarizer
# -------------------------
class Summarizer:
    SYSTEM = (
        "You are a senior physician assistant creating clinical documentation. "
        "Write a SOAP note using ONLY the information provided in the clinical data. "
        "Do not infer, assume, or add any information not explicitly present. "
        "Be precise about who performed actions (patient vs. doctor). "
        "Use exact wording from the source data when describing medications, symptoms, and diagnoses. "
        "If information is missing for a SOAP section, write 'Not documented' rather than fabricating content."
    )

    def __init__(self, max_tokens: int = 400, temperature: float = 0.0):
        self.max_tokens = max_tokens
        self.temperature = temperature

    def run(self, clinical_data: dict) -> Dict[str, Any]:
        # Present clinical_data as JSON to the model
        prompt = (
            "Create a SOAP note using ONLY the information below. "
            "Be extremely literal - do not add, infer, or assume anything. "
            "Distinguish clearly between what the patient reported vs. what the doctor observed/prescribed.\n\n"
            "Clinical Data:\n"
        )
        prompt += json.dumps(clinical_data, indent=2)
        prompt += (
            "\n\nFormat:\n"
            "**Subjective:** Patient's reported symptoms and concerns (use 'patient reports...')\n"
            "**Objective:** Doctor's observations and measurements (use 'doctor noted...' or 'vitals show...')\n"
            "**Assessment:** Diagnoses mentioned (use 'diagnosed with...' or 'suspected...')\n"
            "**Plan:** Treatment prescribed by doctor (use 'doctor prescribed...' not 'patient will take...')\n\n"
            "Be concise but accurate. Only include what's in the data."
        )
        try:
            resp = _llm_call_with_logging(prompt=prompt, system=self.SYSTEM, temperature=self.temperature, max_tokens=self.max_tokens)
            # small sanity check
            if not resp or len(resp.strip()) < 20:
                raise ValueError("Summary too short or empty")
            return {"summary": resp.strip(), "ok": True, "raw_output": resp}
        except Exception as e:
            logger.exception("Summarizer failed")
            return {"summary": "", "ok": False, "error": str(e)}


# -------------------------
# Agent: Validator
# -------------------------
class Validator:
    SYSTEM = (
        "You are a Clinical Safety Auditor. Compare a generated summary against the anonymized source text. "
        "Return a JSON object: {status: 'PASS'|'FAIL', issues: [list], missing_info: [list], hallucinations: [list]}."
    )

    def __init__(self, max_tokens: int = 600, tries: int = 1):
        self.max_tokens = max_tokens
        self.tries = tries

    def run(self, source_text: str, summary: str) -> Dict[str, Any]:
        prompt = (
            "Compare SOURCE (anonymized) and SUMMARY. Return JSON with keys: status (PASS/FAIL), "
            "issues (list of strings), missing_info (list), hallucinations (list). If PASS, issues should be [].\n\n"
            f"SOURCE:\n{source_text}\n\nSUMMARY:\n{summary}\n\nReturn JSON only."
        )
        try:
            resp = _llm_call_with_logging(prompt=prompt, system=self.SYSTEM, temperature=0.0, max_tokens=self.max_tokens)
            parsed = safe_json_loads(resp or "")
            if parsed and isinstance(parsed, dict):
                # normalize status
                parsed["status"] = parsed.get("status", "FAIL")
                parsed.setdefault("issues", [])
                parsed.setdefault("missing_info", [])
                parsed.setdefault("hallucinations", [])
                return {"validation": parsed, "raw_output": resp, "ok": True}
            else:
                return {"validation": {"status": "FAIL", "issues": ["invalid_validator_output"]}, "raw_output": resp, "ok": False}
        except Exception as e:
            logger.exception("Validator error")
            return {"validation": {"status": "FAIL", "issues": [str(e)]}, "raw_output": None, "ok": False}


# -------------------------
# Example pipeline runner
# -------------------------
def run_pipeline_sample(conversation_text: str) -> Dict[str, Any]:
    """
    Run anonymize -> extract -> summarize -> validate on a single conversation.
    Returns the full result dict for logging/evaluation.
    """
    res = {"input_preview": conversation_text[:300]}
    pv = PrivacyGuard()
    extractor = ClinicalExtractor()
    summarizer = Summarizer()
    validator = Validator()

    # anonymize
    anon_res = pv.run(conversation_text)
    res.update({"anonymized": anon_res})

    # extract
    clinical_res = extractor.run(anon_res["anonymized_text"])
    res.update({"clinical": clinical_res})

    # summarize
    summ_res = summarizer.run(clinical_res.get("clinical_data", {}))
    res.update({"summary": summ_res})

    # validate
    val_res = validator.run(anon_res["anonymized_text"], summ_res.get("summary", ""))
    res.update({"validation": val_res})

    # append sample log
    append_jsonl("logs/pipeline_runs.jsonl", {"timestamp": time.time(), "conversation_id": None, "result_preview": {"summary_preview": summ_res.get("summary", "")[:200]}})
    return res


# Quick local test guard
if __name__ == "__main__":
    sample = (
        "Patient: Hi doctor, I'm John Doe and I've had headaches since 01/01/2025. "
        "Contact: 555-123-4567. Doctor: Please take ibuprofen 400mg twice daily."
    )
    out = run_pipeline_sample(sample)
    print(json.dumps(out, indent=2)[:2000])
