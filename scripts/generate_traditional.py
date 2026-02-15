"""
Generate Metropolitan door on door-traditional.png stock photo.

Steps:
1. Analyze door slab bounds in the traditional stock photo
2. Render Metropolitan slab sized to fit
3. Composite onto stock photo
4. Gemini photorealistic enhancement
"""

import os
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
STOCK_PHOTO = ROOT.parent / "bpr-web" / "public" / "door-images" / "door-traditional.png"
OUTPUT_DIR = ROOT / "output" / "metropolitan-traditional"

# ── Step 0: Analyze door slab bounds ──────────────────────────────────

def analyze_door_bounds(img_path: Path):
    """
    Scan the traditional door image to find the door slab region.
    The door is the large white panel in the center between the sidelights.
    We look for the transition from frame/sidelight to door panel.
    """
    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    print(f"Image size: {w}x{h}")

    # Sample horizontal scan lines at different heights to find door edges
    # The door is centered, white, flanked by darker frame moldings

    # Scan at y=500 (middle of door, below the arch, in the panel area)
    scan_y = 500
    pixels = [img.getpixel((x, scan_y)) for x in range(w)]

    print(f"\nHorizontal scan at y={scan_y}:")
    # Find transitions: look for where brightness stays consistently high (white door)
    # vs darker frame edges

    # Print brightness profile in 20px steps
    for x in range(0, w, 20):
        r, g, b = pixels[x]
        brightness = (r + g + b) / 3
        bar = "#" * int(brightness / 10)
        print(f"  x={x:4d}: RGB=({r:3d},{g:3d},{b:3d}) bright={brightness:.0f} {bar}")

    # Also scan at y=300 (upper door area, below arch)
    scan_y2 = 300
    pixels2 = [img.getpixel((x, scan_y2)) for x in range(w)]
    print(f"\nHorizontal scan at y={scan_y2}:")
    for x in range(0, w, 20):
        r, g, b = pixels2[x]
        brightness = (r + g + b) / 3
        bar = "#" * int(brightness / 10)
        print(f"  x={x:4d}: RGB=({r:3d},{g:3d},{b:3d}) bright={brightness:.0f} {bar}")

    # Vertical scan at center x to find top/bottom
    center_x = w // 2
    print(f"\nVertical scan at x={center_x}:")
    for y in range(0, h, 20):
        r, g, b = img.getpixel((center_x, y))
        brightness = (r + g + b) / 3
        bar = "#" * int(brightness / 10)
        print(f"  y={y:4d}: RGB=({r:3d},{g:3d},{b:3d}) bright={brightness:.0f} {bar}")

    return img


def find_door_edges(img_path: Path):
    """
    More precise edge detection using brightness transitions.
    Returns (x1, y1, x2, y2) of the door slab region.
    """
    img = Image.open(img_path).convert("RGB")
    w, h = img.size

    # Scan horizontally at y=500 to find left/right edges
    # The door frame is darker than the white door
    scan_y = 500

    # Find left edge: scan from left, find where brightness jumps high (>200) consistently
    left_edge = None
    for x in range(200, w // 2):
        # Check a small window of pixels
        brightnesses = []
        for dx in range(5):
            r, g, b = img.getpixel((x + dx, scan_y))
            brightnesses.append((r + g + b) / 3)
        avg_bright = sum(brightnesses) / len(brightnesses)

        # Also check the pixel to the left is darker (frame)
        r, g, b = img.getpixel((x - 5, scan_y))
        left_bright = (r + g + b) / 3

        if avg_bright > 200 and left_bright < 180:
            left_edge = x
            break

    # Find right edge: scan from right
    right_edge = None
    for x in range(w - 200, w // 2, -1):
        brightnesses = []
        for dx in range(5):
            r, g, b = img.getpixel((x - dx, scan_y))
            brightnesses.append((r + g + b) / 3)
        avg_bright = sum(brightnesses) / len(brightnesses)

        r, g, b = img.getpixel((x + 5, scan_y))
        right_bright = (r + g + b) / 3

        if avg_bright > 200 and right_bright < 180:
            right_edge = x
            break

    # Find top edge: scan from top at center_x
    center_x = w // 2
    top_edge = None
    for y in range(50, h // 2):
        r, g, b = img.getpixel((center_x, y))
        bright = (r + g + b) / 3
        # Also check pixel above
        r2, g2, b2 = img.getpixel((center_x, y - 5))
        above_bright = (r2 + g2 + b2) / 3

        if bright > 200 and above_bright < 180:
            top_edge = y
            break

    # Find bottom edge: scan from bottom
    bottom_edge = None
    for y in range(h - 50, h // 2, -1):
        r, g, b = img.getpixel((center_x, y))
        bright = (r + g + b) / 3
        r2, g2, b2 = img.getpixel((center_x, y + 3))
        below_bright = (r2 + g2 + b2) / 3

        if bright > 200 and below_bright < 150:
            bottom_edge = y
            break

    print(f"\nDetected door slab bounds:")
    print(f"  Left:   x={left_edge}")
    print(f"  Right:  x={right_edge}")
    print(f"  Top:    y={top_edge}")
    print(f"  Bottom: y={bottom_edge}")

    if all(v is not None for v in [left_edge, right_edge, top_edge, bottom_edge]):
        door_w = right_edge - left_edge
        door_h = bottom_edge - top_edge
        print(f"  Size:   {door_w}x{door_h} px")

    return left_edge, top_edge, right_edge, bottom_edge


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if "--analyze" in sys.argv:
        # Just analyze, don't generate
        analyze_door_bounds(STOCK_PHOTO)
        find_door_edges(STOCK_PHOTO)
        sys.exit(0)

    # Door slab bounds for door-traditional.png (manually verified from pixel analysis)
    # Left/right: frame molding edges at x=390 and x=705
    # Top: below frame header at y=160 (includes arch area — will be overlaid)
    # Bottom: above dark threshold at y=815
    x1, y1, x2, y2 = 390, 160, 705, 815
    door_w = x2 - x1  # 315
    door_h = y2 - y1  # 655
    print(f"Door slab bounds: ({x1},{y1}) to ({x2},{y2}) — {door_w}x{door_h}px")

    # Step 2: Import and render the Metropolitan slab
    print(f"\n=== Step 2: Rendering Metropolitan slab ({door_w}x{door_h}) ===")
    sys.path.insert(0, str(Path(__file__).parent))
    from render_door_slab import render_door_slab

    slab_path = OUTPUT_DIR / "slab-for-composite.png"
    render_door_slab(slab_path, width_px=door_w)

    # Step 3: Composite
    print("\n=== Step 3: Creating composite ===")
    stock = Image.open(STOCK_PHOTO).convert("RGBA")
    slab = Image.open(slab_path).convert("RGBA")

    # Resize slab height to match door region (width already matches)
    slab_resized = slab.resize((door_w, door_h), Image.LANCZOS)
    stock.paste(slab_resized, (x1, y1))

    composite_path = OUTPUT_DIR / "composite-raw.png"
    stock.convert("RGB").save(composite_path)
    print(f"Composite saved: {composite_path}")

    # Step 4: Gemini photorealistic enhancement
    print("\n=== Step 4: Gemini photorealistic enhancement ===")
    api_key = os.environ.get("GOOGLE_AI_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_AI_API_KEY not set")
        sys.exit(1)

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    composite_bytes = composite_path.read_bytes()

    PROMPT = """\
This is a photo of a house entrance with white sidelights. The door panel \
in the center has been digitally composited and looks flat/fake. Make the \
door panel look photorealistic — add real wood grain, realistic groove \
depth and shadows, natural glass translucency. \
The long black bar on the left side of the door is a tall modern \
long-pull door handle — a sleek matte black vertical bar that runs \
almost half the door height, mounted on small standoff brackets. \
Make it look like real brushed matte black metal with subtle light \
reflections, matching the style of high-end modern entry door hardware. \
Keep the EXACT same composition, framing, and every pixel outside \
the door panel completely unchanged. Output the full 1024x1024 image."""

    for i in range(1, 4):
        print(f"  Generating variant {i}...")
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
                    out_path = OUTPUT_DIR / f"traditional-{i}.png"
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

        if i < 3:
            time.sleep(5)

    print(f"\nDone! Check {OUTPUT_DIR}")
