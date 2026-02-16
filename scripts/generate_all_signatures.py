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
import io
import os
import sys
import time
from pathlib import Path

from PIL import Image, ImageFilter

# ── Paths ─────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
DOOR_IMAGES = ROOT.parent / "bpr-web" / "public" / "door-images"
OUTPUT_BASE = ROOT / "output"

# Default stock photo and door slab bounds (door-traditional.png)
DEFAULT_STOCK_PHOTO = DOOR_IMAGES / "door-traditional.png"
DEFAULT_DOOR_BOUNDS = (365, 140, 712, 817)

# Per-stock-photo door bounds
STOCK_PHOTO_BOUNDS = {
    "door-traditional.png": (365, 140, 712, 817),
    "door-craftsman.png": (398, 100, 688, 820),
}

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
    "craftsman": {
        "name": "Craftsman",
        "wood_type": "white-oak",
        "stain_color": "#6B5B4A",
        "stock_photo": "door-craftsman.png",
        "handle": {
            "style": "square-pull",
            "finish": "matte-black",
            "side": "left",
            "heightFromBottom": 40,
        },
        "elements": [
            {"type": "recessed-panel", "position": {"x": 8, "y": 5}, "size": {"width": 20, "height": 22}, "depth": 0.625},
            {"type": "recessed-panel", "position": {"x": 8, "y": 29}, "size": {"width": 20, "height": 22}, "depth": 0.625},
            {"type": "recessed-panel", "position": {"x": 8, "y": 53}, "size": {"width": 20, "height": 22}, "depth": 0.625},
        ],
        "handle_description": "a square-pull door handle — a short matte black vertical bar about 12 inches long, mounted at waist height with standoff brackets. Make it look like real brushed matte black metal",
        "prompt_context": "decorative leaded glass sidelights and a transom window",
    },
}


# ── Gemini prompt builder ─────────────────────────────────────────────

def build_prompt(template: dict) -> str:
    """Build Gemini prompt customized to the template's features."""
    name = template["name"]
    handle_desc = template["handle_description"]
    context = template.get("prompt_context", "white sidelights")

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

    # Build a description of what the door design looks like
    element_counts = {}
    for e in template["elements"]:
        element_counts[e["type"]] = element_counts.get(e["type"], 0) + 1
    design_parts = []
    if "recessed-panel" in element_counts:
        design_parts.append(f"{element_counts['recessed-panel']} recessed panel(s)")
    if "groove" in element_counts:
        design_parts.append(f"{element_counts['groove']} groove(s)")
    if "glass-panel" in element_counts:
        design_parts.append(f"{element_counts['glass-panel']} glass panel(s)")
    design_desc = " and ".join(design_parts) if design_parts else "a flat slab"

    # Build explicit list of what NOT to add
    forbidden = []
    if not has_glass:
        forbidden.append("glass windows, lites, or transoms")
    if not has_grooves:
        forbidden.append("grooves or lines")
    forbidden.append("decorative molding, dentils, or carvings")
    forbidden_text = ", ".join(forbidden)

    return (
        f"This is a photo of a house entrance with {context}. The door panel "
        f"in the center has been digitally composited and looks flat/fake. This is the "
        f"{name} door design. The door has EXACTLY {design_desc} — do NOT change the "
        f"number, size, or layout of these elements. "
        f"Make ONLY the door panel look photorealistic — add {features_text}. "
        f"The hardware on the left side of the door is {handle_desc}. "
        f"CRITICAL: Do NOT add {forbidden_text} to the door. Do NOT redesign the door. "
        f"The composited door layout is the EXACT design — only enhance material realism. "
        f"Keep every pixel outside the door panel completely unchanged. "
        f"Output the full 1024x1024 image."
    )


# ── Pipeline ──────────────────────────────────────────────────────────

def generate_template(slug: str, template: dict, num_variants: int = 3):
    """Run full pipeline for one template."""
    from render_slab_generic import render_door_slab

    # Resolve per-template stock photo and door bounds
    stock_photo_name = template.get("stock_photo", "door-traditional.png")
    stock_photo_path = DOOR_IMAGES / stock_photo_name
    door_x1, door_y1, door_x2, door_y2 = STOCK_PHOTO_BOUNDS.get(
        stock_photo_name, DEFAULT_DOOR_BOUNDS
    )
    door_w = door_x2 - door_x1
    door_h = door_y2 - door_y1

    out_dir = OUTPUT_BASE / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  {template['name']} ({slug})")
    print(f"  Wood: {template['wood_type']}, Stain: {template['stain_color']}")
    print(f"  Elements: {len(template['elements'])}")
    print(f"  Stock photo: {stock_photo_name}")
    print(f"  Door bounds: ({door_x1},{door_y1}) -> ({door_x2},{door_y2}) = {door_w}x{door_h}")
    print(f"{'='*60}")

    # Step 1: Render slab
    slab_path = out_dir / "slab.png"
    render_door_slab(
        slab_path,
        width_px=door_w,
        wood_type=template["wood_type"],
        stain_color=template["stain_color"],
        elements=template["elements"],
        handle=template["handle"],
    )

    # Step 2: Composite
    stock = Image.open(stock_photo_path).convert("RGBA")
    slab = Image.open(slab_path).convert("RGBA")
    slab_resized = slab.resize((door_w, door_h), Image.LANCZOS)
    stock.paste(slab_resized, (door_x1, door_y1))

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

    # Load original stock photo for post-processing (clamp door to bounds)
    original_stock = Image.open(stock_photo_path).convert("RGB")

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

                    # Post-process: extract the door region from Gemini output
                    # and blend it onto the original stock photo. We shrink
                    # the crop inward by MARGIN pixels so the original door
                    # frame/trim is preserved, and feather the edges for a
                    # smooth transition.
                    MARGIN = 15
                    FEATHER = 8
                    gemini_img = Image.open(io.BytesIO(part.inline_data.data)).convert("RGB")
                    gemini_img = gemini_img.resize(original_stock.size, Image.LANCZOS)

                    # Build a soft alpha mask: white in the inner door area,
                    # black outside, with feathered edges for blending.
                    inner_x1 = door_x1 + MARGIN
                    inner_y1 = door_y1 + MARGIN
                    inner_x2 = door_x2 - MARGIN
                    inner_y2 = door_y2 - MARGIN
                    mask = Image.new("L", original_stock.size, 0)
                    from PIL import ImageDraw
                    ImageDraw.Draw(mask).rectangle(
                        [inner_x1, inner_y1, inner_x2, inner_y2], fill=255
                    )
                    mask = mask.filter(ImageFilter.GaussianBlur(radius=FEATHER))

                    final = original_stock.copy()
                    final.paste(gemini_img, (0, 0), mask)
                    final.save(out_path)

                    print(f"    Saved (clamped to door bounds): {out_path}")
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
