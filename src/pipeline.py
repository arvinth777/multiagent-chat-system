from src.agents import LanguageTranslator, PrivacyGuard, ClinicalExtractor, Summarizer, Validator
from src.logger import log_api_call

class ClinicalPipeline:
    def __init__(self):
        self.translator_agent = LanguageTranslator()
        self.privacy_agent = PrivacyGuard()
        self.extractor_agent = ClinicalExtractor()
        self.summarizer_agent = Summarizer()
        self.validator_agent = Validator()

    def run(self, raw_text: str, source_language: str = "English"):
        import time
        
        print("--- Starting Clinical Pipeline ---")
        pipeline_start = time.time()
        timings = {}
        
        # Step 0: Translation (conditional)
        current_text = raw_text
        translation_used = False
        
        if source_language != "English":
            print(f"\n[Agent 0] Translating from {source_language} to English...")
            t0 = time.time()
            trans_result = self.translator_agent.run(raw_text, source_language)
            current_text = trans_result["translated_text"]
            timings['translator'] = time.time() - t0
            translation_used = True
            
            # Log result
            log_api_call("Language Translator", raw_text[:200], current_text[:200])
            print(f" > Translated Text: {current_text[:100]}...")
            if not trans_result.get("ok"):
                print(f"   [Warning] Translation issue: {trans_result.get('error')}")
        
        # Step 1: Privacy Guard
        print("\n[Agent 1] Anonymizing text...")
        t0 = time.time()
        anon_result = self.privacy_agent.run(current_text)
        anonymized_text = anon_result["anonymized_text"]
        timings['privacy_guard'] = time.time() - t0
        
        # Log result
        log_api_call("Privacy Guard", current_text, anonymized_text)
        print(f" > Anonymized Text: {anonymized_text[:100]}...")
        if anon_result.get("used_fallback"):
            print(f"   [Warning] Used fallback: {anon_result.get('note')}")

        # Step 2: Clinical Extractor
        print("\n[Agent 2] Extracting clinical entities...")
        t0 = time.time()
        extract_result = self.extractor_agent.run(anonymized_text)
        extracted_info = extract_result.get("clinical_data", {})
        timings['clinical_extractor'] = time.time() - t0
        
        # Log result
        log_api_call("Clinical Extractor", anonymized_text, extracted_info)
        print(f" > Extracted Info: \n{extracted_info}")

        # Step 3: Summarizer
        print("\n[Agent 3] Generating SOAP note...")
        t0 = time.time()
        summ_result = self.summarizer_agent.run(extracted_info)
        summary = summ_result.get("summary", "Error generating summary")
        timings['summarizer'] = time.time() - t0
        
        # Log result
        log_api_call("Summarizer", extracted_info, summary)
        print(f" > Summary: \n{summary}")

        # Step 4: Clinical Validator
        print("\n[Agent 4] Validating summary...")
        t0 = time.time()
        validation_input = f"Source: {anonymized_text}\nSummary: {summary}"
        val_result = self.validator_agent.run(anonymized_text, summary)
        validation_output = val_result.get("validation", {})
        timings['validator'] = time.time() - t0
        
        # Log result
        log_api_call("Clinical Validator", validation_input, validation_output)
        print(f" > Validation Result: \n{validation_output}")
        
        # Calculate total time
        timings['total'] = time.time() - pipeline_start
        print(f"\n⏱️  Total Processing Time: {timings['total']:.2f}s")

        result = {
            "anonymized_text": anonymized_text,
            "extracted_info": extracted_info,
            "summary": summary,
            "validation_result": validation_output,
            "timings": timings
        }
        
        # Add translation info if used
        if translation_used:
            result["translation"] = {
                "source_language": source_language,
                "original_text": raw_text[:500],  # Store preview
                "translated_text": current_text[:500]
            }
            
            if not trans_result.get("ok"):
                result.setdefault("warnings", []).append(f"Translation failed: {trans_result.get('error')}")
        
        return result
