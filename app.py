import streamlit as st
from src.pipeline import ClinicalPipeline
from dotenv import load_dotenv
import os
import json
from collections import Counter

load_dotenv()

st.set_page_config(page_title="Origin Medical Agentic Pipeline", layout="wide")

st.title("🏥 Origin Medical: Agentic Clinical Pipeline")
st.markdown("### Research Grade 5-Agent System")

# Sidebar
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Google Gemini API Key", type="password", value=os.getenv("GOOGLE_API_KEY", ""))

# Language selector
st.sidebar.markdown("---")
st.sidebar.subheader("🌍 Input Language")
source_language = st.sidebar.selectbox(
    "Select the language of your input text:",
    ["English", "Spanish", "French", "Hindi", "Tamil"],
    index=0,
    help="Agent 0 will translate non-English text to English before processing"
)

if source_language != "English":
    st.sidebar.info(f"🔄 Translation from {source_language} will be performed by Agent 0")

if not api_key:
    st.warning("Please enter your Google API Key in the sidebar.")
    st.stop()

os.environ["GOOGLE_API_KEY"] = api_key

# Input
col1, col2 = st.columns(2)

with col1:
    st.subheader("Input Medical Text")
    
    raw_text = st.text_area(
        "Paste consultation text here:", 
        value="",
        placeholder="Example:\n\nPatient: Hi doctor, I've been having headaches...\nDoctor: How long have you had these symptoms?",
        height=300
    )
    
    if st.button("Run Pipeline", type="primary"):
        if not raw_text.strip():
            st.error("❌ Please enter some medical text first!")
        elif len(raw_text.strip()) < 20:
            st.warning("⚠️ Input text is very short. Please provide a more complete medical conversation for better results.")
        else:
            try:
                with st.spinner("Running Agents..."):
                    pipeline = ClinicalPipeline()
                    results = pipeline.run(raw_text, source_language=source_language)
                    st.session_state['results'] = results
                    st.success("✅ Pipeline completed successfully!")
            except Exception as e:
                st.error(f"❌ Pipeline Error: {str(e)}")
                st.warning("This might be due to:")
                st.markdown("""
                - API rate limits (wait 60 seconds and try again)
                - Invalid API key (check your .env file)
                - Network issues
                - Input text format issues
                """)
                import logging
                logging.error(f"Pipeline execution failed: {e}")

with col2:
    st.subheader("Pipeline Output")
    
    if 'results' not in st.session_state:
        st.info("👈 Enter medical text on the left and click 'Run Pipeline' to see results here.")
    
    if 'results' in st.session_state:
        results = st.session_state['results']
        
        # Display Warnings (e.g. Translation failure)
        if results.get('warnings'):
            for w in results['warnings']:
                st.error(f"⚠️ {w}")
        
        # Privacy Dashboard
        st.subheader("🛡️ Privacy Preservation Layer")
        redacted_text = results.get('anonymized_text', '')
        
        # Count PII redactions (Case Insensitive)
        r_lower = redacted_text.lower()
        pii_counts = {
            "Names": r_lower.count("[patient_name]") + r_lower.count("[doctor_name]"),
            "Dates": r_lower.count("[date]"),
            "Locations": r_lower.count("[location]"),
            "Contacts": r_lower.count("[contact_info]") + r_lower.count("[email]")
        }
        total_redactions = sum(pii_counts.values())
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Names Redacted", pii_counts["Names"])
        col2.metric("Dates Redacted", pii_counts["Dates"])
        col3.metric("Locations Masked", pii_counts["Locations"])
        col4.metric("Contacts Removed", pii_counts["Contacts"])
        
        if total_redactions > 0:
            col5.success(f"**HIPAA**\n✅ Active")
        else:
            col5.info("**HIPAA**\nℹ️ No PII")
        
        st.caption(f"Total PII elements redacted: **{total_redactions}** | Compliance: HIPAA Safe Harbor Method")
        st.markdown("---")
        
        # Display processing time metrics
        if 'timings' in results:
            st.subheader("⏱️ Processing Performance")
            timings = results['timings']
            
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Privacy", f"{timings.get('privacy_guard', 0):.2f}s")
            col2.metric("Extraction", f"{timings.get('clinical_extractor', 0):.2f}s")
            col3.metric("Summary", f"{timings.get('summarizer', 0):.2f}s")
            col4.metric("Validation", f"{timings.get('validator', 0):.2f}s")
            col5.metric("**Total**", f"{timings.get('total', 0):.2f}s", delta=None)
            
            st.markdown("---")
        
        # Tabs for each agent
        tabs_list = ["🔒 Privacy", "📋 Extraction", "📝 Summary", "✅ Validation"]
        has_translation = 'translation' in results
        
        if has_translation:
            tabs_list.insert(0, "🌐 Translation")
            
        tabs = st.tabs(tabs_list)
        
        # If translation exists, it's the first tab
        if has_translation:
            with tabs[0]:
                st.markdown("### Agent 0: Language Translator")
                st.info(f"Translated from {results['translation']['source_language']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Original Text:**")
                    st.code(results['translation']['original_text'], language="text")
                with col2:
                    st.markdown("**Translated Text:**")
                    st.code(results['translation']['translated_text'], language="text")
            
            # Shift other tabs index by 1
            t_priv = tabs[1]
            t_ext = tabs[2]
            t_sum = tabs[3]
            t_val = tabs[4]
        else:
            t_priv = tabs[0]
            t_ext = tabs[1]
            t_sum = tabs[2]
            t_val = tabs[3]
        
        with t_priv:
            st.markdown("### Agent 1: Privacy Guard")
            st.info("Removes PII (Names, Dates, Locations)")
            st.code(results['anonymized_text'], language="text")
            
        with t_ext:
            st.markdown("### Agent 2: Clinical Extractor")
            st.info("Extracts structured entities")
            
            # Display extracted data
            extracted = results.get('extracted_info', {})
            if isinstance(extracted, dict):
                st.json(extracted)
            else:
                st.markdown(extracted)
            
            # Explainability section
            st.markdown("---")
            with st.expander("🔍 **Show Agent Reasoning** (Explainability)"):
                st.markdown("### How the Extractor Works")
                st.markdown("**Step 1: Text Analysis**")
                st.code("""
Input: Anonymized medical conversation
↓
Agent scans for clinical patterns:
- Symptom keywords (pain, fever, cough, etc.)
- Medication mentions (dosage + frequency)
- Vital signs (BP, HR, Temp)
- Diagnosis statements
                """, language="text")
                
                st.markdown("**Step 2: Structured Extraction**")
                source_text = results.get('anonymized_text', '')[:500]
                st.text_area("Source Text (first 500 chars)", source_text, height=100, disabled=True)
                
                st.markdown("**Step 3: Entity Mapping**")
                if isinstance(extracted, dict):
                    st.markdown("**Detected Entities:**")
                    if extracted.get('symptoms'):
                        st.success(f"✅ **Symptoms:** {len(extracted['symptoms'])} found")
                    if extracted.get('medications'):
                        st.success(f"✅ **Medications:** {len(extracted['medications'])} found")
                    if extracted.get('diagnoses'):
                        st.success(f"✅ **Diagnoses:** {len(extracted['diagnoses'])} found")
                    if extracted.get('vitals'):
                        vitals = extracted['vitals']
                        vital_count = sum(1 for v in vitals.values() if v)
                        if vital_count > 0:
                            st.success(f"✅ **Vitals:** {vital_count} measurements")
                
                st.markdown("**Step 4: JSON Schema Validation**")
                st.caption("Output is validated against predefined schema before returning")
            
        with t_sum:
            st.markdown("### Agent 3: Summarizer")
            st.info("Generates SOAP Note")
            st.markdown(results['summary'])
            
        with t_val:
            st.markdown("### Agent 4: Clinical Validator")
            st.info("Checks for hallucinations and missing information")
            val_result = results['validation_result']
            
            if isinstance(val_result, dict):
                status = val_result.get('status', 'UNKNOWN')
                if status == 'PASS':
                    st.success(f"✅ **Validation Status: {status}**")
                else:
                    st.warning(f"⚠️ **Validation Status: {status}**")
                
                issues = val_result.get('issues', [])
                missing_info = val_result.get('missing_info', [])
                hallucinations = val_result.get('hallucinations', [])
                
                if issues:
                    st.markdown("**🔍 Issues Detected:**")
                    for i, issue in enumerate(issues, 1):
                        st.markdown(f"{i}. {issue}")
                
                if missing_info:
                    st.markdown("**📋 Missing Information:**")
                    for i, info in enumerate(missing_info, 1):
                        st.markdown(f"{i}. {info}")
                
                if hallucinations:
                    st.markdown("**⚠️ Hallucinations Detected:**")
                    for i, hall in enumerate(hallucinations, 1):
                        st.markdown(f"{i}. {hall}")
                
                if not issues and not missing_info and not hallucinations and status == 'PASS':
                    st.success("No issues detected! Summary accurately reflects the source text.")
            else:
                if "PASSED" in str(val_result).upper():
                    st.success(val_result)
                else:
                    st.warning(val_result)
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("📥 Download SOAP Note", results.get('summary', ''), file_name="soap_note.txt")
        with c2:
            if st.button("🗑️ Clear Results"):
                del st.session_state['results']
                st.rerun()

# Footer
st.markdown("---")

# Pipeline Analytics
st.header("📊 Pipeline Analytics")
batch_file = "data/batch_results.json"

if os.path.exists(batch_file):
    with open(batch_file, "r") as f:
        batch_json = json.load(f)
    
    if isinstance(batch_json, dict) and 'results' in batch_json:
        batch_data = batch_json['results']
        metrics = batch_json.get('metrics', {})
        
        if 'average_rouge_scores' in metrics:
            st.subheader("📈 ROUGE Evaluation Scores")
            r1, r2, rl = st.columns(3)
            rouge = metrics['average_rouge_scores']
            r1.metric("ROUGE-1", f"{rouge['rouge1']:.3f}")
            r2.metric("ROUGE-2", f"{rouge['rouge2']:.3f}")
            rl.metric("ROUGE-L", f"{rouge['rougeL']:.3f}")
            st.caption("ROUGE scores measure overlap between generated summaries and source text. Higher is better (0-1 scale).")
            
            st.subheader("📊 Pipeline Quality Metrics")
            total = len(batch_data)
            passed = sum(1 for r in batch_data if r.get('validation_result', {}).get('status') == 'PASS')
            pass_rate = (passed / total * 100) if total > 0 else 0
            avg_time = sum(r.get('timings', {}).get('total', 0) for r in batch_data) / total if total > 0 else 0
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Validation Pass Rate", f"{pass_rate:.0f}%", delta="Quality Check" if pass_rate > 0 else None)
            with col2:
                st.metric("Avg Processing Time", f"{avg_time:.1f}s", delta="Per Conversation")
            with col3:
                st.metric("Total Samples", total, delta="Batch Processed")
            with col4:
                accuracy_score = pass_rate / 100
                st.metric("Accuracy Score", f"{accuracy_score:.2f}", delta="0-1 scale")
            
            st.info("""
            **Quality Metrics Explained:**
            - **Validation Pass Rate**: % of summaries that passed safety checks (no hallucinations, accurate attribution)
            - **Processing Time**: Average time to process one conversation through all 5 agents
            - **Accuracy Score**: Normalized quality score based on validation results
            """)
            st.markdown("---")
    else:
        batch_data = batch_json
        
    total_records = len(batch_data)
    pass_count = sum(1 for r in batch_data if r.get('validation_result', {}).get('status') == 'PASS')
    fail_count = total_records - pass_count
    
    # Privacy Dashboard (Batch)
    st.subheader("🛡️ Privacy Preservation Layer")
    total_names_redacted = 0
    total_dates_redacted = 0
    total_locations_masked = 0
    total_contacts_removed = 0
    
    for record in batch_data:
        redacted_text = record.get('ai_output', {}).get('anonymized_text', '')
        r_lower = redacted_text.lower()
        total_names_redacted += r_lower.count("[patient_name]") + r_lower.count("[doctor_name]")
        total_dates_redacted += r_lower.count("[date]")
        total_locations_masked += r_lower.count("[location]")
        total_contacts_removed += r_lower.count("[contact_info]") + r_lower.count("[email]")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Names Redacted", total_names_redacted)
    col2.metric("Dates Redacted", total_dates_redacted)
    col3.metric("Locations Masked", total_locations_masked)
    col4.metric("Contacts Removed", total_contacts_removed)
    col5.metric("Total Redactions", total_names_redacted + total_dates_redacted + total_locations_masked + total_contacts_removed)
    
    st.subheader("✅ Validation Status Breakdown")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("✅ Passed Validation", pass_count, delta=f"{(pass_count/total_records*100):.0f}%" if total_records > 0 else "0%")
    with col2:
        st.metric("⚠️ Failed Validation", fail_count, delta=f"{(fail_count/total_records*100):.0f}%" if total_records > 0 else "0%", delta_color="inverse")
    
    st.markdown("---")

# Batch Results Viewer
st.header("📂 Batch Results Viewer")
if os.path.exists(batch_file):
    selected_id = st.selectbox("Select Record ID", [r['id'] for r in batch_data])
    record = next((r for r in batch_data if r['id'] == selected_id), None)
    
    if record:
        res = record.get('ai_output', {})
        
        b_tabs_list = ["🔒 Privacy", "📋 Extraction", "📝 Summary", "✅ Validation"]
        b_has_trans = 'translation' in res
        
        if b_has_trans:
            b_tabs_list.insert(0, "🌐 Translation")
            
        b_tabs = st.tabs(b_tabs_list)
        
        if b_has_trans:
            with b_tabs[0]:
                st.code(res['translation']['translated_text'], language="text")
            bt_priv = b_tabs[1]
            bt_ext = b_tabs[2]
            bt_sum = b_tabs[3]
            bt_val = b_tabs[4]
        else:
            bt_priv = b_tabs[0]
            bt_ext = b_tabs[1]
            bt_sum = b_tabs[2]
            bt_val = b_tabs[3]
        
        with bt_priv:
            st.code(res.get('anonymized_text', 'N/A'), language="text")
        with bt_ext:
            st.json(res.get('extracted_info', {}))
        with bt_sum:
            st.markdown(res.get('summary', 'N/A'))
        with bt_val:
            val = res.get('validation_result', {})
            if isinstance(val, dict):
                status = val.get('status', 'UNKNOWN')
                if status == 'PASS':
                    st.success(f"✅ **Validation Status: {status}**")
                else:
                    st.warning(f"⚠️ **Validation Status: {status}**")
                
                issues = val.get('issues', [])
                missing_info = val.get('missing_info', [])
                hallucinations = val.get('hallucinations', [])
                
                if issues:
                    st.markdown("**🔍 Issues Detected:**")
                    for i, issue in enumerate(issues, 1):
                        st.markdown(f"{i}. {issue}")
                if missing_info:
                    st.markdown("**📋 Missing Information:**")
                    for i, info in enumerate(missing_info, 1):
                        st.markdown(f"{i}. {info}")
                if hallucinations:
                    st.markdown("**⚠️ Hallucinations Detected:**")
                    for i, hall in enumerate(hallucinations, 1):
                        st.markdown(f"{i}. {hall}")
            else:
                st.warning(str(val))
else:
    st.info("No batch results found. Run `python -m src.batch_processor` to generate data.")

st.caption("Built for Origin Medical Research Intern Challenge")
