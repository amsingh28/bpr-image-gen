"""
Generate photorealistic template door photos using AI image providers.

Usage:
  python scripts/generate_template_photo.py --provider flux-fill
  python scripts/generate_template_photo.py --provider flux-kontext
  python scripts/generate_template_photo.py --provider gemini
  python scripts/generate_template_photo.py --provider claude
  python scripts/generate_template_photo.py --provider all

Env vars required:
  REPLICATE_API_TOKEN  (for flux-fill, flux-kontext)
  GOOGLE_AI_API_KEY    (for gemini)
  ANTHROPIC_API_KEY    (for claude)
"""

import argparse
import base64
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw

# ── Paths ──────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
STOCK_PHOTO = ROOT.parent / "bpr-web" / "public" / "door-images" / "door-modern-2.png"
MASK_PATH = ROOT / "output" / "metropolitan" / "door-modern-2-mask.png"
OUTPUT_DIR = ROOT / "output" / "metropolitan"

# ── Door slab mask bounds (pixel coords in 1024x1024 image) ───────────
# Determined by analyzing RGB transitions at the door frame edges.
# These cover only the door panel — not frame, not sidelights.
DOOR_SLAB_X1 = 398
DOOR_SLAB_Y1 = 136
DOOR_SLAB_X2 = 664
DOOR_SLAB_Y2 = 824

# ── Prompts ────────────────────────────────────────────────────────────

# For mask-based inpainting (Flux Fill) — describes only the door slab
DOOR_ONLY_PROMPT = """\
A solid maple hardwood door slab with a warm medium-brown stain. \
The surface features a distinctive woven groove grid pattern: \
four evenly-spaced thin vertical grooves and eight evenly-spaced \
thin horizontal grooves carved at shallow depth, creating an \
elegant tight lattice texture across the left two-thirds of the \
door face. Along the right edge of the door, a narrow full-height \
frosted glass strip runs from near the top to near the bottom. \
A sleek matte black long-pull bar handle is mounted on the left \
side at waist height. Realistic wood grain texture visible between \
the grooves, natural lighting matching the surrounding photo, \
professional architectural product photography."""

# For non-mask providers — wraps with context to preserve surroundings
CONTEXTUAL_PROMPT = """\
In this photo of a modern house entrance, replace ONLY the center \
door slab (the wood panel between the two glass sidelights) with \
the following door design. Keep the glass sidelights, dark door \
frame, house walls, porch, step, shadows, greenery, and all \
surroundings exactly as they are. Do not change anything except \
the door panel itself.

New door design: A solid maple hardwood door with a warm medium-brown \
stain. The surface features a distinctive woven groove grid pattern — \
four evenly-spaced thin vertical grooves and eight evenly-spaced thin \
horizontal grooves carved at shallow depth, creating an elegant tight \
lattice texture across the left two-thirds of the door face. Along \
the right edge of the door, there is a narrow full-height frosted \
glass strip running from near the top to near the bottom. A sleek \
matte black long-pull bar handle is mounted on the left side at \
waist height. The door should have realistic maple wood grain texture \
visible between the grooves, with natural lighting matching the \
existing photo."""


# ── Helpers ────────────────────────────────────────────────────────────

def ensure_mask():
    """Create the door-slab-only mask if it doesn't exist."""
    if MASK_PATH.exists():
        return
    print(f"Creating mask at {MASK_PATH}")
    img = Image.open(STOCK_PHOTO)
    mask = Image.new("L", img.size, 0)  # black = keep
    draw = ImageDraw.Draw(mask)
    draw.rectangle(
        [DOOR_SLAB_X1, DOOR_SLAB_Y1, DOOR_SLAB_X2, DOOR_SLAB_Y2],
        fill=255,  # white = replace
    )
    mask.save(MASK_PATH)
    print(f"Mask saved: {MASK_PATH}")


def image_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode()


def save_output(provider: str, index: int, image_data: bytes):
    out_path = OUTPUT_DIR / f"{provider}-{index}.png"
    with open(out_path, "wb") as f:
        f.write(image_data)
    print(f"  Saved: {out_path}")


# ── Provider: Flux Fill Pro (inpainting with mask) ─────────────────────

def generate_flux_fill(count: int = 3):
    """Replicate: black-forest-labs/flux-fill-pro"""
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        print("SKIP flux-fill: REPLICATE_API_TOKEN not set")
        return

    import replicate

    ensure_mask()
    print(f"\n=== Flux Fill Pro ({count} variants) ===")

    for i in range(1, count + 1):
        print(f"  Generating variant {i}...")
        output = replicate.run(
            "black-forest-labs/flux-fill-pro",
            input={
                "image": open(STOCK_PHOTO, "rb"),
                "mask": open(MASK_PATH, "rb"),
                "prompt": DOOR_ONLY_PROMPT,
                "steps": 50,
                "guidance": 30,
                "output_format": "png",
                "seed": 42 + i * 1000,
            },
        )
        # output is a FileOutput URL — download it
        import httpx
        resp = httpx.get(str(output))
        save_output("flux-fill", i, resp.content)


# ── Provider: Flux Kontext Pro (text-guided edit) ──────────────────────

def generate_flux_kontext(count: int = 3):
    """Replicate: black-forest-labs/flux-kontext-pro"""
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        print("SKIP flux-kontext: REPLICATE_API_TOKEN not set")
        return

    import replicate

    print(f"\n=== Flux Kontext Pro ({count} variants) ===")

    img_uri = f"data:image/png;base64,{image_to_base64(STOCK_PHOTO)}"

    for i in range(1, count + 1):
        print(f"  Generating variant {i}...")
        output = replicate.run(
            "black-forest-labs/flux-kontext-pro",
            input={
                "prompt": CONTEXTUAL_PROMPT,
                "input_image": img_uri,
                "seed": 42 + i * 1000,
            },
        )
        import httpx
        resp = httpx.get(str(output))
        save_output("flux-kontext", i, resp.content)


# ── Provider: Gemini (Google AI) ───────────────────────────────────────

# Models to try in order of preference
GEMINI_IMAGE_MODELS = [
    "gemini-2.5-flash-image",
    "gemini-2.0-flash-exp-image-generation",
]


def generate_gemini(count: int = 3):
    """Google Gemini: image editing via generateContent"""
    api_key = os.environ.get("GOOGLE_AI_API_KEY")
    if not api_key:
        print("SKIP gemini: GOOGLE_AI_API_KEY not set")
        return

    import time
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    print(f"\n=== Gemini ({count} variants) ===")

    img_bytes = STOCK_PHOTO.read_bytes()

    for i in range(1, count + 1):
        saved = False
        for model in GEMINI_IMAGE_MODELS:
            if model.startswith("imagen"):
                # Imagen uses generate_images API (text-only, no input image)
                print(f"  Variant {i}: trying {model} (text-to-image)...")
                try:
                    response = client.models.generate_images(
                        model=model,
                        prompt=DOOR_ONLY_PROMPT,
                        config=types.GenerateImagesConfig(
                            number_of_images=1,
                        ),
                    )
                    if response.generated_images:
                        img_data = response.generated_images[0].image.image_bytes
                        save_output(f"gemini-{model.split('-')[0]}", i, img_data)
                        saved = True
                        break
                except Exception as e:
                    print(f"    {model} failed: {type(e).__name__}: {str(e)[:150]}")
                    continue
            else:
                # Gemini multimodal: input image + text -> output image
                print(f"  Variant {i}: trying {model}...")
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=[
                            types.Content(
                                parts=[
                                    types.Part.from_bytes(
                                        data=img_bytes, mime_type="image/png"
                                    ),
                                    types.Part.from_text(text=CONTEXTUAL_PROMPT),
                                ],
                            ),
                        ],
                        config=types.GenerateContentConfig(
                            response_modalities=["IMAGE", "TEXT"],
                        ),
                    )
                    # Extract image from response
                    for part in response.candidates[0].content.parts:
                        if (
                            part.inline_data
                            and part.inline_data.mime_type.startswith("image/")
                        ):
                            save_output("gemini", i, part.inline_data.data)
                            saved = True
                            break
                    if saved:
                        break
                    # No image — print text
                    for part in response.candidates[0].content.parts:
                        if part.text:
                            print(f"    Text: {part.text[:150]}")
                except Exception as e:
                    print(f"    {model} failed: {type(e).__name__}: {str(e)[:150]}")
                    continue

        if not saved:
            print(f"  WARNING: No image generated for variant {i} (all models failed)")

        # Brief pause between variants to respect rate limits
        if i < count:
            time.sleep(5)


# ── Provider: Claude (Anthropic) ───────────────────────────────────────

def generate_claude(count: int = 3):
    """Anthropic Claude: image generation with reference"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("SKIP claude: ANTHROPIC_API_KEY not set")
        return

    import anthropic

    client = anthropic.Anthropic()

    print(f"\n=== Claude ({count} variants) ===")

    # Claude generate-from-scratch prompt (no input image editing)
    CLAUDE_PROMPT = """\
Create a photorealistic image of a modern house entrance with a custom \
hardwood entry door. The scene shows a contemporary white stucco home \
exterior with clean architectural lines, bright natural daylight, and \
a slight shadow cast to the right. The entrance has a dark-framed \
doorway with two tall frosted glass sidelights flanking the main door.

The door itself is solid maple wood with a warm medium-brown stain. \
Its surface features a distinctive woven groove grid pattern: four \
evenly-spaced thin vertical grooves and eight evenly-spaced thin \
horizontal grooves carved at shallow depth, creating an elegant tight \
lattice texture across the left two-thirds of the door face. Along \
the right edge of the door, there is a narrow full-height frosted \
glass strip running from near the top to near the bottom. A sleek \
matte black long-pull bar handle is mounted on the left side at \
waist height.

The porch has a small concrete step. There is minimal modern \
landscaping with a potted plant on the right side. Professional \
architectural photography style, sharp focus, realistic wood grain \
texture, 8K quality."""

    for i in range(1, count + 1):
        print(f"  Generating variant {i}...")
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=16384,
            messages=[
                {
                    "role": "user",
                    "content": CLAUDE_PROMPT,
                },
            ],
        )

        # Extract image from response content blocks
        saved = False
        for block in response.content:
            if getattr(block, "type", None) == "image":
                img_data = base64.b64decode(block.source.data)
                save_output("claude", i, img_data)
                saved = True
                break
        if not saved:
            print(f"  WARNING: No image in response for variant {i}")
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    print(f"    Text: {block.text[:200]}")


# ── Main ───────────────────────────────────────────────────────────────

PROVIDERS = {
    "flux-fill": generate_flux_fill,
    "flux-kontext": generate_flux_kontext,
    "gemini": generate_gemini,
    "claude": generate_claude,
}


def main():
    parser = argparse.ArgumentParser(description="Generate template door photos")
    parser.add_argument(
        "--provider",
        choices=[*PROVIDERS.keys(), "all"],
        default="all",
        help="Which AI provider to use",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=3,
        help="Number of variants per provider (default: 3)",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.provider == "all":
        for name, fn in PROVIDERS.items():
            fn(count=args.count)
    else:
        PROVIDERS[args.provider](count=args.count)

    print(f"\nDone! Check {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
