import requests
import base64
import os

def generate_latex_from_image(image_path, api_key):
    """
    Uses Gemini 1.5 Flash to convert an image of a math equation into LaTeX.
    """
    if not api_key:
        return None, "Error: No Gemini API Key provided. Set it in Settings -> AI Key."

    if not os.path.exists(image_path):
        return None, f"Error: Image not found at {image_path}"

    try:
        # 1. Read and Encode Image
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

        # 2. Prepare API Call
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": "You are a math OCR expert. Looking at this image, provide the LaTeX code for the equation shown. Return ONLY the LaTeX string. Do not include triple backticks, code blocks, or explanations. If there is no math, return an empty string."},
                        {
                            "inline_data": {
                                "mime_type": "image/png", # Could be guessed, but Flash handles PNG/JPG well
                                "data": encoded_image
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.95,
                "topK": 40,
                "maxOutputTokens": 1024,
            }
        }

        # 3. Call Gemini
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            return None, f"Gemini API Error ({response.status_code}): {response.text}"

        res_json = response.json()
        
        # 4. Extract Result
        try:
            latex = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
            # Clean up potential markdown backticks if the model ignored instructions
            if latex.startswith("```"):
                latex = latex.replace("```latex", "").replace("```", "").strip()
            return latex, "Success"
        except (KeyError, IndexError):
            return None, f"Unexpected response format from Gemini: {res_json}"

    except Exception as e:
        return None, f"Jeanie Error: {str(e)}"

def batch_generate_alt_text(image_paths, api_key, progress_callback=None):
    """
    (Placeholder for future batch AI alt-text features)
    """
    results = {}
    total = len(image_paths)
    for i, path in enumerate(image_paths):
        # Implementation would go here
        pass
    return results
