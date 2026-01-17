# 🚀 Deployment Guide

This guide will help you deploy the Multi-Agent Clinical Summarization Pipeline to Streamlit Cloud.

## 📋 Prerequisites

Before deploying, ensure you have:
- ✅ A GitHub account
- ✅ A Google Gemini API key ([Get one here](https://ai.google.dev/))
- ✅ This repository pushed to your GitHub account

---

## 🌐 Deploy to Streamlit Cloud

### Step 1: Push to GitHub

If you haven't already, push this repository to GitHub:

```bash
git add .
git commit -m "Add Streamlit demo configuration"
git push origin main
```

### Step 2: Connect to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io/)
2. Sign in with your GitHub account
3. Click **"New app"**
4. Select your repository: `yourusername/multiagent-chat-system`
5. Set the main file path: `app.py`
6. Click **"Advanced settings"**

### Step 3: Configure Secrets

In the **Advanced settings** section, add your API key to the secrets:

```toml
GOOGLE_API_KEY = "your_actual_gemini_api_key_here"
```

> **Note**: Replace `your_actual_gemini_api_key_here` with your real API key from Google AI Studio.

### Step 4: Deploy

1. Click **"Deploy"**
2. Wait 2-3 minutes for the app to build and deploy
3. Your app will be live at: `https://yourusername-multiagent-chat-system.streamlit.app`

---

## 🖥️ Local Development

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/multiagent-chat-system.git
   cd multiagent-chat-system
   ```

2. **Create virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your GOOGLE_API_KEY
   ```

### Run Locally

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

---

## 🧪 Testing the Demo

### Quick Test

1. Open the app (locally or deployed)
2. Enter your Google Gemini API key in the sidebar (if not configured in secrets)
3. Paste this sample medical conversation:

```
Patient: Hi doctor, I've been having severe headaches for the past 3 days.
Doctor: Can you describe the pain? Where is it located?
Patient: It's mostly on the right side of my head, throbbing pain.
Doctor: Any other symptoms like nausea or sensitivity to light?
Patient: Yes, I feel nauseous and bright lights make it worse.
Doctor: This sounds like a migraine. I'll prescribe Sumatriptan 50mg. Take one tablet at the onset of symptoms.
```

4. Click **"Run Pipeline"**
5. Verify all 5 agent tabs display results:
   - 🔒 Privacy (PII redaction)
   - 📋 Extraction (structured entities)
   - 📝 Summary (SOAP note)
   - ✅ Validation (quality check)

### Multilingual Test

1. Select **"Spanish"** from the language dropdown
2. Paste this Spanish conversation:

```
Paciente: Hola doctor, tengo dolor de cabeza y fiebre.
Doctor: ¿Cuánto tiempo ha tenido estos síntomas?
Paciente: Desde ayer por la noche.
```

3. Verify the **🌐 Translation** tab appears with translated text

---

## 🔧 Troubleshooting

### Issue: "API Key Error"

**Solution:**
- Verify your API key is correct
- Check that it's properly set in Streamlit Cloud secrets or `.env` file
- Ensure the key has not expired

### Issue: "Rate Limit Exceeded"

**Solution:**
- Gemini Free Tier has rate limits (15 RPM)
- Wait 60 seconds between requests
- Consider upgrading to a paid tier for production use

### Issue: "No batch results found"

**Solution:**
- This is normal on first deployment
- Run batch processing to generate analytics data:
  ```bash
  python -m src.batch_processor
  ```
- The analytics dashboard will populate after batch processing completes

### Issue: "Module not found"

**Solution:**
- Ensure all dependencies are installed:
  ```bash
  pip install -r requirements.txt
  ```
- If deploying to Streamlit Cloud, check the deployment logs for missing packages

### Issue: App is slow or times out

**Solution:**
- Gemini API calls can take 5-15 seconds per agent
- Total pipeline time: 20-60 seconds for complex conversations
- This is expected behavior with the free tier
- Consider implementing caching for repeated inputs

---

## 📊 Generating Analytics Data

The app displays analytics from `data/batch_results.json`. To generate this:

```bash
# Download dataset (first time only)
python src/data_loader.py

# Run batch processing
python -m src.batch_processor
```

This processes 5 medical dialogues and generates metrics for the dashboard.

---

## 🔒 Security Best Practices

### For Streamlit Cloud:
- ✅ Always use Streamlit secrets for API keys
- ✅ Never commit `.env` files with real keys
- ✅ Use `.gitignore` to exclude sensitive files

### For Local Development:
- ✅ Keep `.env` file local (already in `.gitignore`)
- ✅ Use `.env.example` as a template
- ✅ Rotate API keys periodically

---

## 🆘 Getting Help

If you encounter issues:

1. **Check the logs:**
   - Streamlit Cloud: Click "Manage app" → "Logs"
   - Local: Terminal output where you ran `streamlit run app.py`

2. **Review documentation:**
   - [Streamlit Docs](https://docs.streamlit.io/)
   - [Google Gemini API Docs](https://ai.google.dev/docs)

3. **Common fixes:**
   - Restart the app
   - Clear Streamlit cache: Click "☰" → "Clear cache"
   - Check API key permissions

---

## 📝 Updating the Deployment

To update your deployed app:

```bash
git add .
git commit -m "Update app"
git push origin main
```

Streamlit Cloud will automatically redeploy when it detects changes to your repository.

---

## 🎯 Next Steps

After successful deployment:

1. ✅ Test all features thoroughly
2. ✅ Add the live demo link to your README
3. ✅ Share the demo with stakeholders
4. ✅ Monitor usage and performance
5. ✅ Consider upgrading API tier for production use

---

**Questions?** Open an issue on GitHub or contact the maintainer.
