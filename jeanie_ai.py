import requests
import base64
import os


def check_connectivity():
    """
    Fast check for internet connectivity.
    Used to warn users if school firewall is blocking access.
    """
    try:
        # Google is the most reliable ping for "is the internet working"
        requests.get("https://www.google.com", timeout=3)
        return True
    except:
        return False


def validate_api_key(api_key):
    """
    Sends a minimal request to Gemini to check if the key is valid.
    Returns: (is_valid, message)
    """
    if not api_key:
        return False, "No API Key provided."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    headers = {"Content-Type": "application/json"}

    # Simple text prompt
    payload = {
        "contents": [{"parts": [{"text": "Hello"}]}],
        "generationConfig": {
            "maxOutputTokens": 5,
        },
    }

    import time

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)

            if response.status_code == 200:
                return True, "Success! Key is valid."
            elif response.status_code == 429:
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                else:
                    return False, "Quota Exceeded (429): Please wait a minute."
            else:
                # Parse error message
                try:
                    err_json = response.json()
                    msg = err_json.get("error", {}).get("message", response.text)
                    return False, f"API Error: {msg}"
                except:
                    return False, f"API Error ({response.status_code}): {response.text}"

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return False, f"Connection Failed: {str(e)}"

    return False, "Validation Timed Out"


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

        # 2. Determine MIME type based on file extension
        _, ext = os.path.splitext(image_path.lower())
        mime_type_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
        }
        mime_type = mime_type_map.get(ext, "image/png")  # Default to PNG if unknown

        # 3. Prepare API Call
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

        headers = {"Content-Type": "application/json"}

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": "You are a math OCR and accessibility expert. Convert the math equation and any related teacher notes in this image into clean LaTeX code. "
                            "The image may contain a mix of professional typed math and handwritten notes. "
                            "Ensure the LaTeX is accurate and formatted for Canvas LMS (MathJax). "
                            "Return ONLY the LaTeX string. Do not include triple backticks, code blocks, or explanations. "
                            "If you see a complex formula, use standard LaTeX structures. If there is no math, return an empty string."
                        },
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": encoded_image,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.95,
                "topK": 40,
                "maxOutputTokens": 1024,
            },
        }

        # 3. Call Gemini with Retry (Enhanced Resilience)
        import time

        max_retries = 5
        base_delay = 3

        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)

                if response.status_code == 200:
                    break
                elif response.status_code == 429:
                    wait_time = base_delay * (2**attempt)
                    print(f"    ⏳ Rate limit hit. Pausing for {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    return (
                        None,
                        f"Gemini API Error ({response.status_code}): {response.text}",
                    )
            except Exception as e:
                error_str = str(e).lower()
                is_retryable = (
                    "10054" in error_str
                    or "connection" in error_str
                    or "timeout" in error_str
                    or "remote host" in error_str
                )

                if is_retryable and attempt < max_retries - 1:
                    wait_time = base_delay * (2**attempt)
                    print(
                        f"    ⏳ Network hiccup ({error_str[:30]}...). Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    raise e

        if response.status_code != 200:
            return None, f"Gemini API Error ({response.status_code}): {response.text}"

        res_json = response.json()

        # 4. Extract Result
        try:
            latex = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Clean up potential markdown backticks if the model ignored instructions
            if latex.startswith("```"):
                latex = latex.replace("```latex", "").replace("```", "").strip()

            # Add delay to prevent rate limiting on next request
            time.sleep(1)  # Wait 1 second between successful requests

            return latex, "Success"
        except (KeyError, IndexError):
            return None, f"Unexpected response format from Gemini: {res_json}"

    except Exception as e:
        return None, f"MOSH Magic Error: {str(e)}"


def generate_table_from_image(image_path, api_key):
    """
    Uses Gemini 2.0 Flash to convert an image of a table into an accessible HTML table.
    Returns extracted HTML table string.
    """
    if not api_key:
        return None, "Error: No Gemini API Key provided."

    if not os.path.exists(image_path):
        return None, f"Error: Image not found at {image_path}"

    try:
        # 1. Read and Encode Image
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

        # 2. Determine MIME type based on file extension
        _, ext = os.path.splitext(image_path.lower())
        mime_type_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
        }
        mime_type = mime_type_map.get(ext, "image/png")  # Default to PNG if unknown

        # 3. Prepare API Call
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

        headers = {"Content-Type": "application/json"}

        prompt = (
            "You are a document OCR and accessibility expert. Convert the table shown in this image into a clean, accessible HTML table. "
            "Use <table>, <thead>, <tbody>, <tr>, <th> (for headers), and <td> tags. "
            "Ensure the structure is clean and accurately reflects the image. "
            "Return ONLY the <table>...</table> HTML. Do not include markdown backticks, <html>/<body> tags, or explanations."
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": encoded_image,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.95,
                "topK": 40,
                "maxOutputTokens": 4096,
            },
        }

        # 3. Call Gemini
        import time

        max_retries = 3
        for attempt in range(max_retries):
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                break
            elif response.status_code == 429 and attempt < max_retries - 1:
                time.sleep(5)
                continue
            else:
                return (
                    None,
                    f"Gemini API Error ({response.status_code}): {response.text}",
                )

        res_json = response.json()

        # 4. Extract Result
        try:
            table_html = res_json["candidates"][0]["content"]["parts"][0][
                "text"
            ].strip()
            # Clean up backticks if needed
            if table_html.startswith("```"):
                table_html = (
                    table_html.replace("```html", "").replace("```", "").strip()
                )
            return table_html, "Success"
        except (KeyError, IndexError):
            return None, f"Unexpected response format from Gemini."

    except Exception as e:
        return None, f"MOSH Magic Table OCR Error: {str(e)}"


def generate_text_from_scanned_image(image_path, api_key):
    """
    Uses Gemini 1.5 Flash to perform OCR on a scanned document image.
    Returns extracted text formatted for HTML.
    """
    if not api_key:
        return None, "Error: No Gemini API Key provided."

    if not os.path.exists(image_path):
        return None, f"Error: Image not found at {image_path}"

    try:
        # 1. Read and Encode Image
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

        # 2. Determine MIME type based on file extension
        _, ext = os.path.splitext(image_path.lower())
        mime_type_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
        }
        mime_type = mime_type_map.get(ext, "image/png")  # Default to PNG if unknown

        # 3. Prepare API Call
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

        headers = {"Content-Type": "application/json"}

        prompt = (
            "You are a document OCR expert. Extract ALL text from this scanned document image. "
            "Preserve the reading order. Do not include triple backticks or explanations. "
            "Format the output as simple, clean text without any markdown symbols."
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": encoded_image,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.95,
                "topK": 40,
                "maxOutputTokens": 2048,
            },
        }

        # 3. Call Gemini
        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code != 200:
            return None, f"Gemini API Error ({response.status_code}): {response.text}"

        res_json = response.json()

        # 4. Extract Result
        try:
            extracted_text = res_json["candidates"][0]["content"]["parts"][0][
                "text"
            ].strip()
            return extracted_text, "Success"
        except (KeyError, IndexError):
            return None, f"Unexpected response format from Gemini."

    except Exception as e:
        return None, f"MOSH Magic Error: {str(e)}"


def generate_alt_text_from_image(image_path, api_key, context=None):
    """
    Uses Gemini 1.5 Flash to generate descriptive alt text for an image.
    """
    if not api_key:
        return None, "Error: No Gemini API Key provided."

    if not os.path.exists(image_path):
        return None, f"Error: Image not found at {image_path}"

    try:
        # 1. Read and Encode Image
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

        # 2. Determine MIME type based on file extension
        _, ext = os.path.splitext(image_path.lower())
        mime_type_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
        }
        mime_type = mime_type_map.get(ext, "image/png")  # Default to PNG if unknown

        # 3. Prepare API Call
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

        headers = {"Content-Type": "application/json"}

        prompt = "You are an accessibility expert. Write a very brief, concise alt text for this image (under 120 characters if possible). "
        if context:
            prompt += f"Context: '{context}'. "
        prompt += "Return ONLY the text. No 'Image of', 'Alt text:', or period at the end unless it's a full sentence. If decorative, return 'Decorative'."

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": encoded_image,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "topP": 0.95,
                "topK": 40,
                "maxOutputTokens": 256,
            },
        }

        # 3. Call Gemini with Retry Logic (Enhanced)
        import time

        max_retries = 5
        base_delay = 3

        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)

                if response.status_code == 200:
                    break
                elif response.status_code == 429:
                    wait_time = base_delay * (2**attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    return (
                        None,
                        f"Gemini API Error ({response.status_code}): {response.text}",
                    )
            except Exception as e:
                error_str = str(e).lower()
                is_retryable = (
                    "10054" in error_str
                    or "connection" in error_str
                    or "timeout" in error_str
                    or "remote host" in error_str
                )

                if is_retryable and attempt < max_retries - 1:
                    wait_time = base_delay * (2**attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    raise e

        if response.status_code != 200:
            return None, f"Gemini API Error ({response.status_code}): {response.text}"

        res_json = response.json()

        # 4. Extract Result
        try:
            alt_text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()

            # Add delay to prevent rate limiting on next request
            time.sleep(1)  # Wait 1 second between successful requests

            return alt_text, "Success"
        except (KeyError, IndexError):
            return None, f"Unexpected response format from Gemini."

    except Exception as e:
        return None, f"MOSH Magic Error: {str(e)}"


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
