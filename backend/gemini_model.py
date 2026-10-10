import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

logger = logging.getLogger("kec_gemini_model")

# Load environment variables
load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
)

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing from .env")

client = genai.Client(api_key=api_key)

FALLBACK_MODELS = [
    model_name,
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-flash-latest"
]

def generate_answer(question: str, context: str, language: str = "Tamil") -> str:
    prompt = f"""
நீங்கள் Kongu Engineering College (KEC)-க்கான
AI Assistant.

முக்கிய விதிகள்:
1. மாணவர் தமிழில் கேட்டால் தமிழில் பதிலளிக்கவும்.
2. ஆங்கிலத்தில் கேட்டால் ஆங்கிலத்தில் பதிலளிக்கவும்.
3. கொடுக்கப்பட்ட கல்லூரி தகவல்களை முதன்மையாகப் பயன்படுத்தவும்.
4. ஆதாரமில்லாத கல்லூரி விவரங்களை உருவாக்க வேண்டாம்.
5. ஒரே வாக்கியத்தை மீண்டும் மீண்டும் கூற வேண்டாம்.
6. கேள்விக்குப் பொருத்தமான, தெளிவான விளக்கத்தை வழங்கவும்.
7. தகவல் இல்லையென்றால் அதைத் தெளிவாகத் தெரிவிக்கவும்.
8. தேவையற்ற தகவல்களைச் சேர்க்க வேண்டாம்.
9. கிடைத்த source URL-களைப் பயன்படுத்தவும்.

பதில் மொழி: {language}

கல்லூரி தகவல்கள்:
<context>
{context}
</context>

மாணவரின் கேள்வி:
{question}

மேலே உள்ள தகவல்களின் அடிப்படையில் கேள்விக்குப் பதிலளிக்கவும்.
தகவல் போதுமானதாக இல்லாவிட்டால், உறுதிப்படுத்த முடியவில்லை
என்று தெரிவிக்கவும்.
"""

    models_to_try = [model_name] + [m for m in FALLBACK_MODELS if m != model_name]

    for model in models_to_try:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=600
                )
            )

            answer = response.text

            if answer and answer.strip():
                return answer.strip()
        except Exception as e:
            logger.warning(f"Error generating answer with model '{model}': {e}")
            continue

    return "மன்னிக்கவும், தற்போது பதிலை உருவாக்க முடியவில்லை."
