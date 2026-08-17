import json
import time
from typing import Dict
from google import genai
from google.genai import types
from google.genai.errors import APIError
from app.config import settings
from app.prompt import PROMPT_TEMPLATE

ai_client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Fallback sequence in order of preference
MODELS_TO_TRY = [
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite"
]

def generate_product_copy(
    name: str, 
    specs: str, 
    focus_keyphrase: str, 
    sku: str = "", 
    feedback_error: str = ""
) -> Dict[str, str]:
    prompt = PROMPT_TEMPLATE.format(name=name, specs=specs, fk=focus_keyphrase, sku=sku or "None")
    
    if feedback_error:
        prompt += f"\n\nCRITICAL FIX REQUIRED FROM PREVIOUS ATTEMPT:\n{feedback_error}"

    last_exception = None

    for model_name in MODELS_TO_TRY:
        # Retry loop for temporary 503 capacity spikes per model
        for attempt in range(3):
            try:
                chat = ai_client.chats.create(
                    model=model_name,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json",
                    )
                )
                response = chat.send_message(prompt)
                
                raw_text = response.text or ""
                try:
                    data = json.loads(raw_text)
                    return {
                        "sku": data.get("sku", "").strip(),
                        "description": data.get("description", "").strip()
                    }
                except json.JSONDecodeError:
                    # Fallback parsing if output isn't strict JSON
                    fallback_sku = sku or f"MAAT-{name.replace(' ', '-').upper()[:15]}"
                    return {
                        "sku": fallback_sku,
                        "description": raw_text
                    }

            except APIError as e:
                last_exception = e
                # Check for 503 error code
                if e.code == 503 or "503" in str(e):
                    time.sleep(1.5 * (attempt + 1))  # Short backoff
                    continue
                # For non-503 errors (e.g. 404), break loop to try next model immediately
                break

    raise RuntimeError(f"All model attempts failed. Last error: {last_exception}")