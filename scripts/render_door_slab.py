"""
Render a door slab from a ModernDoorConfig as a PNG image using PIL.
Draws wood base color, groove grid, glass panels, and handle.

This produces a structural reference image that can be fed to an AI
model alongside a stock photo for photorealistic compositing.
"""

from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path

# ── Metropolitan config values ────────────────────────────────────────

DOOR_W_INCHES = 36
DOOR_H_INCHES = 80
WOOD_COLOR = (139, 115, 85)  # #8B7355 maple stain
HANDLE_COLOR = (30, 30, 30)  # matte black
GLASS_COLOR = (180, 200, 210, 180)  # frosted glass with alpha
GROOVE_COLOR = (70, 55, 40)  # dark shadow in grooves

# Elements from SIG_METROPOLITAN
GLASS_PANELS = [
    {"x": 27, "y": 5, "w": 4, "h": 70},
]

VERTICAL_GROOVES = [
    {"x": 8, "y": 5, "w": 0.5, "h": 70},
    {"x": 13.5, "y": 5, "w": 0.5, "h": 70},
    {"x": 19, "y": 5, "w": 0.5, "h": 70},
    {"x": 24.5, "y": 5, "w": 0.5, "h": 70},
]

HORIZONTAL_GROOVES = [
    {"x": 8, "y": 5, "w": 17, "h": 0.5},
    {"x": 8, "y": 14.5, "w": 17, "h": 0.5},
    {"x": 8, "y": 24, "w": 17, "h": 0.5},
    {"x": 8, "y": 33.5, "w": 17, "h": 0.5},
    {"x": 8, "y": 43, "w": 17, "h": 0.5},
    {"x": 8, "y": 52.5, "w": 17, "h": 0.5},
    {"x": 8, "y": 62, "w": 17, "h": 0.5},
    {"x": 8, "y": 71.5, "w": 17, "h": 0.5},
]

# Handle: long-pull, left side, 40" from bottom
HANDLE = {"side": "left", "height_from_bottom": 40, "inset": 5.5}


def render_door_slab(
    output_path: Path,
    width_px: int = 540,  # Target pixel width
):
    """Render Metropolitan door slab as a PNG."""
    scale = width_px / DOOR_W_INCHES
    height_px = int(DOOR_H_INCHES * scale)

    def to_px(inches):
        return int(inches * scale)

    # Create RGBA image
    img = Image.new("RGBA", (width_px, height_px), WOOD_COLOR + (255,))
    draw = ImageDraw.Draw(img)

    # Add subtle vertical wood grain lines
    import random
    random.seed(42)
    for x in range(0, width_px, 3):
        opacity = random.randint(5, 25)
        shift = random.randint(-10, 10)
        grain_color = (
            max(0, min(255, WOOD_COLOR[0] + shift)),
            max(0, min(255, WOOD_COLOR[1] + shift)),
            max(0, min(255, WOOD_COLOR[2] + shift)),
            opacity + 200,
        )
        draw.line([(x, 0), (x, height_px)], fill=grain_color, width=1)

    # Add horizontal grain variation
    for y in range(0, height_px, 7):
        opacity = random.randint(3, 15)
        shift = random.randint(-8, 8)
        grain_color = (
            max(0, min(255, WOOD_COLOR[0] + shift)),
            max(0, min(255, WOOD_COLOR[1] + shift)),
            max(0, min(255, WOOD_COLOR[2] + shift)),
            opacity + 230,
        )
        draw.line([(0, y), (width_px, y)], fill=grain_color, width=1)

    # Draw grooves (vertical)
    for g in VERTICAL_GROOVES:
        x1 = to_px(g["x"])
        y1 = to_px(g["y"])
        x2 = x1 + max(to_px(g["w"]), 2)
        y2 = y1 + to_px(g["h"])
        # Main groove
        draw.rectangle([x1, y1, x2, y2], fill=GROOVE_COLOR)
        # Highlight edge (right side, lighter)
        highlight = (
            min(255, WOOD_COLOR[0] + 20),
            min(255, WOOD_COLOR[1] + 20),
            min(255, WOOD_COLOR[2] + 20),
        )
        draw.line([(x2 + 1, y1), (x2 + 1, y2)], fill=highlight, width=1)

    # Draw grooves (horizontal)
    for g in HORIZONTAL_GROOVES:
        x1 = to_px(g["x"])
        y1 = to_px(g["y"])
        x2 = x1 + to_px(g["w"])
        y2 = y1 + max(to_px(g["h"]), 2)
        draw.rectangle([x1, y1, x2, y2], fill=GROOVE_COLOR)
        # Highlight edge (bottom, lighter)
        highlight = (
            min(255, WOOD_COLOR[0] + 20),
            min(255, WOOD_COLOR[1] + 20),
            min(255, WOOD_COLOR[2] + 20),
        )
        draw.line([(x1, y2 + 1), (x2, y2 + 1)], fill=highlight, width=1)

    # Draw glass panels
    glass_overlay = Image.new("RGBA", (width_px, height_px), (0, 0, 0, 0))
    glass_draw = ImageDraw.Draw(glass_overlay)
    for gp in GLASS_PANELS:
        x1 = to_px(gp["x"])
        y1 = to_px(gp["y"])
        x2 = x1 + to_px(gp["w"])
        y2 = y1 + to_px(gp["h"])
        glass_draw.rectangle([x1, y1, x2, y2], fill=GLASS_COLOR)
        # Frosted effect: add a diagonal reflection line
        glass_draw.line(
            [(x1 + 5, y1 + 20), (x2 - 2, y1 + 80)],
            fill=(255, 255, 255, 60),
            width=2,
        )
    img = Image.alpha_composite(img, glass_overlay)
    draw = ImageDraw.Draw(img)

    # Draw handle (long-pull bar — tall sleek vertical bar ~48" long)
    handle_x = to_px(HANDLE["inset"]) - 3  # left side
    handle_center_y = height_px - to_px(HANDLE["height_from_bottom"])
    handle_half_h = to_px(24)  # long pull ~48" tall
    handle_w = max(to_px(0.75), 6)

    # Handle shadow (offset to suggest standoff from door)
    draw.rectangle(
        [handle_x + 3, handle_center_y - handle_half_h + 3,
         handle_x + handle_w + 3, handle_center_y + handle_half_h + 3],
        fill=(15, 15, 15, 100),
    )
    # Handle bar
    draw.rectangle(
        [handle_x, handle_center_y - handle_half_h,
         handle_x + handle_w, handle_center_y + handle_half_h],
        fill=HANDLE_COLOR,
    )
    # Handle highlight (left edge gleam)
    draw.line(
        [(handle_x + 1, handle_center_y - handle_half_h),
         (handle_x + 1, handle_center_y + handle_half_h)],
        fill=(90, 90, 90),
        width=1,
    )
    # Handle top/bottom mounting brackets
    bracket_h = to_px(1.5)
    for by in [handle_center_y - handle_half_h, handle_center_y + handle_half_h - bracket_h]:
        draw.rectangle(
            [handle_x - 2, by, handle_x + handle_w + 2, by + bracket_h],
            fill=(25, 25, 25),
        )

    # Add subtle top-to-bottom lighting gradient
    gradient = Image.new("RGBA", (width_px, height_px), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(gradient)
    for y in range(height_px):
        # Slightly lighter at top, darker at bottom
        t = y / height_px
        alpha = int(t * 30)  # max 30 alpha darkening at bottom
        grad_draw.line([(0, y), (width_px, y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, gradient)

    # Convert to RGB and save
    final = img.convert("RGB")
    final.save(output_path)
    print(f"Door slab rendered: {output_path} ({width_px}x{height_px})")
    return final


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent.parent / "output" / "metropolitan"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Full-size slab (for reference)
    render_door_slab(out_dir / "slab-reference.png", width_px=540)

    # Sized to match the stock photo door region (266x688)
    render_door_slab(out_dir / "slab-for-composite.png", width_px=266)
