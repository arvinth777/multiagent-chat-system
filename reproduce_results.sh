#!/bin/bash

# Reproducibility Script for Origin Medical Pipeline
# This script installs dependencies, downloads data, and runs the batch processor.

echo "🚀 Starting Reproduction Script..."

# 1. Install Dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# 2. Download Data
if [ ! -f "data/medical_data.csv" ]; then
    echo "⬇️ Downloading dataset..."
    python src/data_loader.py
else
    echo "✅ Dataset found."
fi

# 3. Run Batch Processor
echo "⚙️ Running Batch Processor (this may take 1-2 minutes)..."
python -m src.batch_processor

# 4. Completion
echo "✅ Reproduction Complete!"
echo "📊 Results saved to data/batch_results.json"
echo "👉 Run 'streamlit run app.py' to view the dashboard."
