import os
import pandas as pd
from dotenv import load_dotenv
from src.pipeline import ClinicalPipeline

# Load environment variables
load_dotenv()

def main():
    # Check for API Key
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY not found in .env file.")
        print("Please create a .env file with your API key.")
        return

    # Load real medical data
    data_file = "data/medical_data.csv"
    if not os.path.exists(data_file):
        print(f"Error: {data_file} not found.")
        print("Run: python src/data_loader.py to download the dataset first.")
        return
    
    # Load one sample from real data
    df = pd.read_csv(data_file)
    sample_text = df.iloc[0]['text']
    
    print("=" * 60)
    print("TESTING CLINICAL PIPELINE WITH REAL DATA")
    print("=" * 60)
    print(f"\nProcessing record from: {data_file}")
    print(f"Sample text (first 200 chars): {sample_text[:200]}...\n")

    pipeline = ClinicalPipeline()
    result = pipeline.run(sample_text)
    
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f"\nValidation Status: {result.get('validation_result', {}).get('status', 'UNKNOWN')}")
    if 'timings' in result:
        print(f"Total Processing Time: {result['timings']['total']:.2f}s")

if __name__ == "__main__":
    main()
