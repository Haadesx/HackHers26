import os
import sys
import base64
import json
import httpx
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    print("Error: OPENROUTER_API_KEY is not set in .env")
    sys.exit(1)

def encode_image(image_path: str) -> str:
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        sys.exit(1)
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

async def compare_faces(ref_image_path: str, live_image_path: str):
    ref_b64 = encode_image(ref_image_path)
    live_b64 = encode_image(live_image_path)

    model = "qwen/qwen3-vl-30b-a3b-thinking"

    prompt = """
    You are an AI face matcher. You are given two images:
    1. A reference photo of a person (Image 1).
    2. A live webcam frame of a person (Image 2).
    
    Are they the exact same person? Look closely at facial structures, eye shape, nose shape, and jawline.
    Respond strictly in JSON format:
    {
        "is_same_person": true or false,
        "confidence": <float between 0.0 and 1.0>,
        "reasoning": "brief explanation comparing the facial features"
    }
    """
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://hackhers.demo",
        "X-Title": "DeepfakeGate"
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt.strip()},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{ref_b64}"
                        }
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{live_b64}"
                        }
                    }
                ]
            }
        ],
        "response_format": {"type": "json_object"}
    }
    
    print(f"Sending images to OpenRouter using {model}...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            message = data["choices"][0]["message"]["content"].strip()
            
            # Clean markdown if present
            if message.startswith("```json"):
                message = message[7:-3].strip()
            elif message.startswith("```"):
                message = message[3:-3].strip()
                
            result = json.loads(message)
            print("\n--- OPENROUTER RESULT ---")
            print(json.dumps(result, indent=2))
            print("-------------------------\n")
        
    except Exception as e:
        print(f"Error calling OpenRouter: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_google_face_match.py <reference_img_path> <live_img_path>")
        sys.exit(1)
        
    asyncio.run(compare_faces(sys.argv[1], sys.argv[2]))
