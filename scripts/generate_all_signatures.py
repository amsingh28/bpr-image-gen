"""
Generate photorealistic images for all Signature single-door templates.

Uses the door-traditional.png stock photo (white sidelights) as the base.
Pipeline: render PIL slab → composite onto stock photo → Gemini enhancement.

Usage:
  python scripts/generate_all_signatures.py
  python scripts/generate_all_signatures.py --template metropolitan
  python scripts/generate_all_signatures.py --variants 1
"""

import argparse
import os
import sys
import time
from pathlib import Path

from PIL import Image

# ── Paths ─────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
STOCK_PHOTO = ROOT.parent / "bpr-web" / "public" / "door-images" / "door-traditional.png"
OUTPUT_BASE = ROOT / "output"

# Door slab bounds for door-traditional.png (from fine-grained pixel analysis)
# Left: brightness jumps 75→199 at x=365; Right: drops 185→92 at x=712
# Top: door surface starts at y=140; Bottom: drops 182→88 at y=817
DOOR_X1, DOOR_Y1 = 365, 140
DOOR_X2, DOOR_Y2 = 712, 817
DOOR_W = DOOR_X2 - DOOR_X1  # 347
DOOR_H = DOOR_Y2 - DOOR_Y1  # 677

# ── Template configs ──────────────────────────────────────────────────
# Extracted from bpr-backend/app/services/door_templates.py

SIGNATURE_TEMPLATES = {
    "metropolitan": {
        "name": "Metropolitan",
        "wood_type": "maple",
        "stain_color": "#8B7355",
        "handle": {
            "style": "long-pull",
            "finish": "matte-black",
            "side": "left",
            "heightFromBottom": 40,
        },
        "elements": [
            {"type": "glass-panel", "position": {"x": 27, "y": 5}, "size": {"width": 4, "height": 70}, "glassType": "frosted"},
            {"type": "groove", "position": {"x": 8, "y": 5}, "size": {"width": 0.5, "height": 70}, "direction": "vertical", "depth": 0.25},
            {"type": "groove", "position": {"x": 13.5, "y": 5}, "size": {"width": 0.5, "height": 70}, "direction": "vertical", "depth": 0.25},
            {"type": "groove", "position": {"x": 19, "y": 5}, "size": {"width": 0.5, "height": 70}, "direction": "vertical", "depth": 0.25},
            {"type": "groove", "position": {"x": 24.5, "y": 5}, "size": {"width": 0.5, "height": 70}, "direction": "vertical", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 5}, "size": {"width": 17, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 14.5}, "size": {"width": 17, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 24}, "size": {"width": 17, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 33.5}, "size": {"width": 17, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 43}, "size": {"width": 17, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 52.5}, "size": {"width": 17, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 62}, "size": {"width": 17, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 71.5}, "size": {"width": 17, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
        ],
        "handle_description": "a tall modern long-pull door handle — a sleek matte black vertical bar that runs almost half the door height, mounted on small standoff brackets. Make it look like real brushed matte black metal",
    },
    "art-deco": {
        "name": "Art Deco",
        "wood_type": "walnut",
        "stain_color": "#3B2314",
        "handle": {
            "style": "long-pull",
            "finish": "brass",
            "side": "left",
            "heightFromBottom": 40,
        },
        "elements": [
            {"type": "recessed-panel", "position": {"x": 12, "y": 30}, "size": {"width": 12, "height": 12}, "depth": 0.75},
            {"type": "recessed-panel", "position": {"x": 10, "y": 28}, "size": {"width": 16, "height": 16}, "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 20}, "size": {"width": 20, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 24}, "size": {"width": 20, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 47}, "size": {"width": 20, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 51}, "size": {"width": 20, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 55}, "size": {"width": 20, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 59}, "size": {"width": 20, "height": 0.5}, "direction": "horizontal", "depth": 0.75},
            {"type": "groove", "position": {"x": 8, "y": 63}, "size": {"width": 20, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 5}, "size": {"width": 0.5, "height": 70}, "direction": "vertical", "depth": 0.25},
            {"type": "groove", "position": {"x": 27.5, "y": 5}, "size": {"width": 0.5, "height": 70}, "direction": "vertical", "depth": 0.25},
            {"type": "groove", "position": {"x": 14, "y": 5}, "size": {"width": 0.5, "height": 15}, "direction": "vertical", "depth": 0.75},
            {"type": "groove", "position": {"x": 21.5, "y": 5}, "size": {"width": 0.5, "height": 15}, "direction": "vertical", "depth": 0.75},
        ],
        "handle_description": "a tall modern long-pull door handle — a sleek brass vertical bar that runs almost half the door height, mounted on small standoff brackets. Make it look like real polished brass with warm golden reflections",
    },
    "cathedral": {
        "name": "Cathedral",
        "wood_type": "white-oak",
        "stain_color": "#6B5B4A",
        "handle": {
            "style": "square-pull",
            "finish": "brushed-nickel",
            "side": "left",
            "heightFromBottom": 40,
        },
        "elements": [
            {"type": "glass-panel", "position": {"x": 9, "y": 5}, "size": {"width": 8, "height": 40}, "glassType": "frosted"},
            {"type": "glass-panel", "position": {"x": 19, "y": 5}, "size": {"width": 8, "height": 40}, "glassType": "frosted"},
            {"type": "recessed-panel", "position": {"x": 9, "y": 48}, "size": {"width": 8, "height": 24}, "depth": 0.625},
            {"type": "recessed-panel", "position": {"x": 19, "y": 48}, "size": {"width": 8, "height": 24}, "depth": 0.625},
            {"type": "groove", "position": {"x": 8, "y": 46}, "size": {"width": 20, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 73.5}, "size": {"width": 20, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 17.5, "y": 5}, "size": {"width": 0.5, "height": 69}, "direction": "vertical", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 5}, "size": {"width": 0.5, "height": 69}, "direction": "vertical", "depth": 0.625},
            {"type": "groove", "position": {"x": 27.5, "y": 5}, "size": {"width": 0.5, "height": 69}, "direction": "vertical", "depth": 0.625},
        ],
        "handle_description": "a square-pull door handle — a short brushed nickel vertical bar about 12 inches long, mounted at waist height with standoff brackets. Make it look like real brushed stainless steel with subtle directional grain",
    },
    "grand-estate": {
        "name": "Grand Estate",
        "wood_type": "oak",
        "stain_color": "#5C4033",
        "handle": {
            "style": "square-pull",
            "finish": "bronze",
            "side": "left",
            "heightFromBottom": 40,
        },
        "elements": [
            {"type": "recessed-panel", "position": {"x": 8, "y": 5}, "size": {"width": 9, "height": 20}, "depth": 0.625},
            {"type": "recessed-panel", "position": {"x": 19, "y": 5}, "size": {"width": 9, "height": 20}, "depth": 0.625},
            {"type": "recessed-panel", "position": {"x": 8, "y": 28}, "size": {"width": 9, "height": 20}, "depth": 0.625},
            {"type": "recessed-panel", "position": {"x": 19, "y": 28}, "size": {"width": 9, "height": 20}, "depth": 0.625},
            {"type": "recessed-panel", "position": {"x": 8, "y": 51}, "size": {"width": 9, "height": 20}, "depth": 0.625},
            {"type": "recessed-panel", "position": {"x": 19, "y": 51}, "size": {"width": 9, "height": 20}, "depth": 0.625},
            {"type": "groove", "position": {"x": 17.5, "y": 3}, "size": {"width": 0.5, "height": 74}, "direction": "vertical", "depth": 0.375},
            {"type": "groove", "position": {"x": 8, "y": 3}, "size": {"width": 20, "height": 0.5}, "direction": "horizontal", "depth": 0.375},
            {"type": "groove", "position": {"x": 8, "y": 26}, "size": {"width": 20, "height": 0.5}, "direction": "horizontal", "depth": 0.375},
            {"type": "groove", "position": {"x": 8, "y": 49}, "size": {"width": 20, "height": 0.5}, "direction": "horizontal", "depth": 0.375},
            {"type": "groove", "position": {"x": 8, "y": 72}, "size": {"width": 20, "height": 0.5}, "direction": "horizontal", "depth": 0.375},
            {"type": "groove", "position": {"x": 8, "y": 3}, "size": {"width": 0.5, "height": 74}, "direction": "vertical", "depth": 0.375},
            {"type": "groove", "position": {"x": 27.5, "y": 3}, "size": {"width": 0.5, "height": 74}, "direction": "vertical", "depth": 0.375},
        ],
        "handle_description": "a square-pull door handle — a short oil-rubbed bronze vertical bar about 12 inches long, mounted at waist height with standoff brackets. Make it look like real aged bronze with warm dark patina",
    },
    "botanical": {
        "name": "Botanical",
        "wood_type": "mahogany",
        "stain_color": "#4E2E28",
        "handle": {
            "style": "long-pull",
            "finish": "bronze",
            "side": "left",
            "heightFromBottom": 40,
        },
        "elements": [
            {"type": "recessed-panel", "position": {"x": 10, "y": 8}, "size": {"width": 16, "height": 28}, "depth": 1.0},
            {"type": "recessed-panel", "position": {"x": 9, "y": 40}, "size": {"width": 18, "height": 14}, "depth": 0.5},
            {"type": "recessed-panel", "position": {"x": 9, "y": 57}, "size": {"width": 18, "height": 14}, "depth": 0.375},
            {"type": "groove", "position": {"x": 8, "y": 6}, "size": {"width": 20, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 37}, "size": {"width": 20, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 55}, "size": {"width": 20, "height": 0.5}, "direction": "horizontal", "depth": 0.375},
            {"type": "groove", "position": {"x": 8, "y": 73}, "size": {"width": 20, "height": 0.5}, "direction": "horizontal", "depth": 0.25},
            {"type": "groove", "position": {"x": 8, "y": 6}, "size": {"width": 0.5, "height": 67.5}, "direction": "vertical", "depth": 0.25},
        ],
        "handle_description": "a tall modern long-pull door handle — a sleek oil-rubbed bronze vertical bar that runs almost half the door height, mounted on small standoff brackets. Make it look like real aged bronze with warm dark patina and subtle highlights",
    },
}


# ── Gemini prompt builder ─────────────────────────────────────────────

def build_prompt(template: dict) -> str:
    """Build Gemini prompt customized to the template's features."""
    name = template["name"]
    handle_desc = template["handle_description"]

    has_glass = any(e["type"] == "glass-panel" for e in template["elements"])
    has_panels = any(e["type"] == "recessed-panel" for e in template["elements"])
    has_grooves = any(e["type"] == "groove" for e in template["elements"])

    features = []
    if has_grooves:
        features.append("realistic groove depth and shadows")
    if has_panels:
        features.append("realistic recessed panel depth with proper shadow and light")
    if has_glass:
        features.append("natural glass translucency with subtle reflections")
    features.append("real wood grain texture")

    features_text = ", ".join(features)

    return (
        f"This is a photo of a house entrance with white sidelights. The door panel "
        f"in the center has been digitally composited and looks flat/fake. This is the "
        f"{name} door design. Make the door panel look photorealistic — add {features_text}. "
        f"The hardware on the left side of the door is {handle_desc}, matching the style "
        f"of high-end modern entry door hardware. "
        f"Keep the EXACT same composition, framing, and every pixel outside "
        f"the door panel completely unchanged. Output the full 1024x1024 image."
    )


# ── Pipeline ──────────────────────────────────────────────────────────

def generate_template(slug: str, template: dict, num_variants: int = 3):
    """Run full pipeline for one template."""
    from render_slab_generic import render_door_slab

    out_dir = OUTPUT_BASE / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  {template['name']} ({slug})")
    print(f"  Wood: {template['wood_type']}, Stain: {template['stain_color']}")
    print(f"  Elements: {len(template['elements'])}")
    print(f"{'='*60}")

    # Step 1: Render slab
    slab_path = out_dir / "slab.png"
    render_door_slab(
        slab_path,
        width_px=DOOR_W,
        wood_type=template["wood_type"],
        stain_color=template["stain_color"],
        elements=template["elements"],
        handle=template["handle"],
    )

    # Step 2: Composite
    stock = Image.open(STOCK_PHOTO).convert("RGBA")
    slab = Image.open(slab_path).convert("RGBA")
    slab_resized = slab.resize((DOOR_W, DOOR_H), Image.LANCZOS)
    stock.paste(slab_resized, (DOOR_X1, DOOR_Y1))

    composite_path = out_dir / "composite.png"
    stock.convert("RGB").save(composite_path)
    print(f"Composite saved: {composite_path}")

    # Step 3: Gemini enhancement
    api_key = os.environ.get("GOOGLE_AI_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_AI_API_KEY not set — skipping Gemini step")
        return

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    composite_bytes = composite_path.read_bytes()
    prompt = build_prompt(template)

    for i in range(1, num_variants + 1):
        print(f"  Gemini variant {i}/{num_variants}...")
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[
                    types.Content(
                        parts=[
                            types.Part.from_bytes(data=composite_bytes, mime_type="image/png"),
                            types.Part.from_text(text=prompt),
                        ],
                    ),
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

            saved = False
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    out_path = out_dir / f"variant-{i}.png"
                    out_path.write_bytes(part.inline_data.data)
                    print(f"    Saved: {out_path}")
                    saved = True
                    break
                if part.text:
                    print(f"    Text: {part.text[:200]}")
            if not saved:
                print(f"    WARNING: No image in response")

        except Exception as e:
            print(f"    ERROR: {type(e).__name__}: {str(e)[:200]}")

        if i < num_variants:
            time.sleep(5)


def main():
    parser = argparse.ArgumentParser(description="Generate all Signature door template photos")
    parser.add_argument(
        "--template",
        choices=[*SIGNATURE_TEMPLATES.keys(), "all"],
        default="all",
        help="Which template to generate (default: all)",
    )
    parser.add_argument(
        "--variants",
        type=int,
        default=3,
        help="Number of Gemini variants per template (default: 3)",
    )
    args = parser.parse_args()

    if args.template == "all":
        templates = SIGNATURE_TEMPLATES
    else:
        templates = {args.template: SIGNATURE_TEMPLATES[args.template]}

    for slug, config in templates.items():
        generate_template(slug, config, num_variants=args.variants)

    print(f"\nAll done! Check {OUTPUT_BASE}/")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    main()
