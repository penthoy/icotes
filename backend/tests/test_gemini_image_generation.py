"""
Minimal regression test for Gemini 2.5 Flash Image Preview (Nano Banana) image generation.

This replaces numerous exploratory scripts that were used during initial integration.
It verifies that:
 1. The model returns at least one image object in response. 
 2. The first image contains a data URI we can decode.
 3. We can successfully decode and write the image to disk.

To run (inside backend directory):
    uv run python -m tests.test_gemini_image_generation

Environment:
  Requires OPENROUTER_API_KEY to be set.
"""
from __future__ import annotations
import os
import re
import base64
from icpy.agent.clients import get_openrouter_client

TEST_PROMPT = "Generate a tiny simple icon of a blue circle on white background"


def generate_image(prompt: str = TEST_PROMPT):
    client = get_openrouter_client()
    response = client.chat.completions.create(
        model="google/gemini-2.5-flash-image-preview",
        messages=[{"role": "user", "content": prompt}],
    )
    return response


def extract_first_image_data(response) -> str | None:
    if not response.choices:
        return None
    msg = response.choices[0].message
    if hasattr(msg, "images") and msg.images:
        first = msg.images[0]
        # Dict format with image_url
        if isinstance(first, dict):
            if "image_url" in first:
                iu = first["image_url"]
                if isinstance(iu, dict) and "url" in iu:
                    return iu["url"]
                if isinstance(iu, str):
                    return iu
            if "image_data" in first:
                id_ = first["image_data"]
                if isinstance(id_, dict) and "data" in id_:
                    return id_["data"]
                if isinstance(id_, str):
                    return id_
        elif isinstance(first, str):
            return first
        elif hasattr(first, "data"):
            return getattr(first, "data")
    return None


def save_data_uri(data_uri: str, filename_prefix: str = "nano_banana_test") -> str:
    if not data_uri.startswith("data:image/"):
        raise ValueError("Not a data URI image")
    m = re.match(r"data:image/([a-zA-Z0-9.+-]+);base64,(.+)", data_uri)
    if not m:
        raise ValueError("Malformed data URI")
    ext, b64 = m.groups()
    image_bytes = base64.b64decode(b64)
    out_name = f"{filename_prefix}.{ext}"
    with open(out_name, "wb") as f:
        f.write(image_bytes)
    return out_name


def run_test():
    print("=== Gemini Image Generation Smoke Test ===")
    resp = generate_image()
    img_data_uri = extract_first_image_data(resp)
    if not img_data_uri:
        raise SystemExit("FAIL: No image data found in response")
    print(f"Found image data URI length: {len(img_data_uri)}")
    path = save_data_uri(img_data_uri)
    size = os.path.getsize(path)
    if size == 0:
        raise SystemExit("FAIL: Saved file is empty")
    print(f"Saved image to {path} ({size} bytes)")
    print("PASS: Image generation working")


if __name__ == "__main__":
    run_test()
