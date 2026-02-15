"""
Two-step template photo generation:
1. Composite the rendered door slab onto the stock photo (rough overlay)
2. Feed the composite + isolated slab to Gemini to make it photorealistic

Usage:
  python scripts/composite_and_generate.py
"""

import os
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
STOCK_PHOTO = ROOT.parent / "bpr-web" / "public" / "door-images" / "door-modern-2.png"
SLAB_RENDER = ROOT / "output" / "metropolitan" / "slab-reference.png"
OUTPUT_DIR = ROOT / "output" / "metropolitan"

# Door slab region in the 1024x1024 stock photo
DOOR_X1, DOOR_Y1 = 398, 136
DOOR_X2, DOOR_Y2 = 664, 824
DOOR_W = DOOR_X2 - DOOR_X1  # 266
DOOR_H = DOOR_Y2 - DOOR_Y1  # 688


def create_composite():
    """Paste the rendered slab onto the stock photo in the door region."""
    stock = Image.open(STOCK_PHOTO).convert("RGBA")
    slab = Image.open(SLAB_RENDER).convert("RGBA")

    # Resize slab to fit the door region
    slab_resized = slab.resize((DOOR_W, DOOR_H), Image.LANCZOS)

    # Paste onto stock photo
    stock.paste(slab_resized, (DOOR_X1, DOOR_Y1))

    composite_path = OUTPUT_DIR / "composite-raw.png"
    stock.convert("RGB").save(composite_path)
    print(f"Raw composite saved: {composite_path}")
    return composite_path


def generate_photorealistic(composite_path: Path, count: int = 3):
    """Feed composite + slab reference to Gemini for photorealistic blending."""
    api_key = os.environ.get("GOOGLE_AI_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_AI_API_KEY not set")
        return

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    composite_bytes = composite_path.read_bytes()

    # Single-image prompt — just the composite, simple instruction
    PROMPT = """\
This is a photo of a house entrance. The door panel in the center \
has been digitally composited and looks flat/fake. Make the door \
panel look photorealistic — add real wood grain, realistic groove \
depth and shadows, natural glass translucency. \
The long black bar on the left side of the door is a tall modern \
long-pull door handle — a sleek matte black vertical bar that runs \
almost half the door height, mounted on small standoff brackets. \
Make it look like real brushed matte black metal with subtle light \
reflections, matching the style of high-end modern entry door hardware. \
Keep the EXACT same composition, framing, and every pixel outside \
the door panel completely unchanged. Output the full 1024x1024 image."""

    for i in range(1, count + 1):
        print(f"  Generating photorealistic variant {i}...")
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[
                    types.Content(
                        parts=[
                            types.Part.from_bytes(
                                data=composite_bytes, mime_type="image/png"
                            ),
                            types.Part.from_text(text=PROMPT),
                        ],
                    ),
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

            saved = False
            for part in response.candidates[0].content.parts:
                if (
                    part.inline_data
                    and part.inline_data.mime_type.startswith("image/")
                ):
                    out_path = OUTPUT_DIR / f"photorealistic-{i}.png"
                    out_path.write_bytes(part.inline_data.data)
                    print(f"  Saved: {out_path}")
                    saved = True
                    break
                if part.text:
                    print(f"    Text: {part.text[:200]}")
            if not saved:
                print(f"  WARNING: No image in response for variant {i}")

        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {str(e)[:200]}")

        if i < count:
            time.sleep(5)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Create composite
    print("=== Step 1: Creating composite ===")
    composite_path = create_composite()

    # Step 2: Generate photorealistic versions
    print("\n=== Step 2: Generating photorealistic versions ===")
    generate_photorealistic(composite_path, count=3)

    print(f"\nDone! Check {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
