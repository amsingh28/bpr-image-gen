"""
Generic door slab renderer — renders any template config as a PIL image.

Accepts template parameters (wood color, elements, handle) and produces
a structural reference PNG for AI compositing.
"""

import random
from pathlib import Path
from PIL import Image, ImageDraw


# ── Wood type → base RGB color mapping ────────────────────────────────

WOOD_COLORS = {
    "oak":       (160, 130, 90),   # warm golden oak
    "walnut":    (75, 50, 35),     # dark rich walnut
    "mahogany":  (100, 55, 45),    # deep reddish-brown
    "maple":     (139, 115, 85),   # warm medium maple
    "white-oak": (140, 125, 100),  # lighter warm oak
}

# ── Handle finish → RGB color mapping ─────────────────────────────────

HANDLE_COLORS = {
    "matte-black":    (30, 30, 30),
    "brushed-nickel": (170, 170, 165),
    "brass":          (180, 150, 50),
    "bronze":         (120, 85, 55),
}

# ── Glass type → RGBA color ───────────────────────────────────────────

GLASS_COLORS = {
    "frosted": (180, 200, 210, 180),
    "rain":    (170, 195, 215, 160),
    "seeded":  (185, 200, 195, 170),
    "clear":   (200, 220, 235, 120),
}


def render_door_slab(
    output_path: Path,
    width_px: int,
    *,
    door_w_inches: float = 36.0,
    door_h_inches: float = 80.0,
    wood_type: str = "maple",
    stain_color: str = "#8B7355",
    elements: list[dict] = None,
    handle: dict = None,
) -> Image.Image:
    """
    Render a door slab as a PNG image.

    Args:
        output_path: Where to save the PNG
        width_px: Target pixel width
        door_w_inches: Door width in inches
        door_h_inches: Door height in inches
        wood_type: One of oak, walnut, mahogany, maple, white-oak
        stain_color: Hex color string (used to tint base wood color)
        elements: List of element dicts with type, position, size, etc.
        handle: Handle dict with style, finish, side, heightFromBottom
    """
    if elements is None:
        elements = []
    if handle is None:
        handle = {"style": "long-pull", "finish": "matte-black", "side": "left", "heightFromBottom": 40}

    scale = width_px / door_w_inches
    height_px = int(door_h_inches * scale)

    def to_px(inches):
        return int(inches * scale)

    # Parse stain color to blend with wood base
    wood_base = WOOD_COLORS.get(wood_type, (139, 115, 85))
    stain_rgb = hex_to_rgb(stain_color)
    # Blend: 60% wood base + 40% stain for natural look
    blended = tuple(int(w * 0.6 + s * 0.4) for w, s in zip(wood_base, stain_rgb))

    groove_color = tuple(max(0, c - 50) for c in blended)
    highlight_color = tuple(min(255, c + 20) for c in blended)

    # Create RGBA image with wood base
    img = Image.new("RGBA", (width_px, height_px), blended + (255,))
    draw = ImageDraw.Draw(img)

    # Wood grain texture
    random.seed(42)
    for x in range(0, width_px, 3):
        opacity = random.randint(5, 25)
        shift = random.randint(-10, 10)
        grain = (
            max(0, min(255, blended[0] + shift)),
            max(0, min(255, blended[1] + shift)),
            max(0, min(255, blended[2] + shift)),
            opacity + 200,
        )
        draw.line([(x, 0), (x, height_px)], fill=grain, width=1)

    for y in range(0, height_px, 7):
        opacity = random.randint(3, 15)
        shift = random.randint(-8, 8)
        grain = (
            max(0, min(255, blended[0] + shift)),
            max(0, min(255, blended[1] + shift)),
            max(0, min(255, blended[2] + shift)),
            opacity + 230,
        )
        draw.line([(0, y), (width_px, y)], fill=grain, width=1)

    # ── Draw elements ─────────────────────────────────────────────────

    # Separate by type for layering order: panels first, grooves, glass last
    panels = [e for e in elements if e["type"] == "recessed-panel"]
    grooves = [e for e in elements if e["type"] == "groove"]
    glass_panels = [e for e in elements if e["type"] == "glass-panel"]

    # Draw recessed panels — panel surface close to wood color,
    # with beveled edges (shadow top/left, highlight bottom/right)
    for p in panels:
        x1 = to_px(p["position"]["x"])
        y1 = to_px(p["position"]["y"])
        x2 = x1 + to_px(p["size"]["width"])
        y2 = y1 + to_px(p["size"]["height"])
        depth = p.get("depth", 0.375)

        # Panel surface is only very slightly darker than surrounding wood
        slight_darken = int(depth * 8)
        panel_color = tuple(max(0, c - slight_darken) for c in blended)
        draw.rectangle([x1, y1, x2, y2], fill=panel_color)

        # Bevel width scales with depth (deeper = wider bevel)
        bevel_w = max(2, int(depth * 6))

        # Outer bevel: shadow on top/left edges (light comes from upper-left)
        shadow_dark = tuple(max(0, c - 40 - int(depth * 25)) for c in blended)
        shadow_mid = tuple(max(0, c - 25 - int(depth * 15)) for c in blended)
        for i in range(bevel_w):
            t = i / max(bevel_w, 1)
            shadow = tuple(int(sd * (1 - t) + sm * t) for sd, sm in zip(shadow_dark, shadow_mid))
            draw.line([(x1 + i, y1 + i), (x2 - i, y1 + i)], fill=shadow, width=1)  # top
            draw.line([(x1 + i, y1 + i), (x1 + i, y2 - i)], fill=shadow, width=1)  # left

        # Outer bevel: highlight on bottom/right edges
        highlight_bright = tuple(min(255, c + 30 + int(depth * 15)) for c in blended)
        highlight_soft = tuple(min(255, c + 15 + int(depth * 8)) for c in blended)
        for i in range(bevel_w):
            t = i / max(bevel_w, 1)
            hl = tuple(int(hb * (1 - t) + hs * t) for hb, hs in zip(highlight_bright, highlight_soft))
            draw.line([(x1 + i, y2 - i), (x2 - i, y2 - i)], fill=hl, width=1)  # bottom
            draw.line([(x2 - i, y1 + i), (x2 - i, y2 - i)], fill=hl, width=1)  # right

    # Draw grooves
    for g in grooves:
        x1 = to_px(g["position"]["x"])
        y1 = to_px(g["position"]["y"])
        x2 = x1 + max(to_px(g["size"]["width"]), 2)
        y2 = y1 + max(to_px(g["size"]["height"]), 2)

        draw.rectangle([x1, y1, x2, y2], fill=groove_color)

        direction = g.get("direction", "horizontal")
        if direction == "vertical":
            draw.line([(x2 + 1, y1), (x2 + 1, y2)], fill=highlight_color, width=1)
        else:
            draw.line([(x1, y2 + 1), (x2, y2 + 1)], fill=highlight_color, width=1)

    # Draw glass panels (on overlay for alpha blending)
    if glass_panels:
        glass_overlay = Image.new("RGBA", (width_px, height_px), (0, 0, 0, 0))
        glass_draw = ImageDraw.Draw(glass_overlay)
        for gp in glass_panels:
            x1 = to_px(gp["position"]["x"])
            y1 = to_px(gp["position"]["y"])
            x2 = x1 + to_px(gp["size"]["width"])
            y2 = y1 + to_px(gp["size"]["height"])

            glass_type = gp.get("glassType", "frosted")
            color = GLASS_COLORS.get(glass_type, GLASS_COLORS["frosted"])
            glass_draw.rectangle([x1, y1, x2, y2], fill=color)

            # Frosted reflection line
            glass_draw.line(
                [(x1 + 5, y1 + 20), (x2 - 2, y1 + 80)],
                fill=(255, 255, 255, 60),
                width=2,
            )
        img = Image.alpha_composite(img, glass_overlay)
        draw = ImageDraw.Draw(img)

    # ── Draw handle ───────────────────────────────────────────────────

    handle_style = handle.get("style", "long-pull")
    handle_finish = handle.get("finish", "matte-black")
    handle_side = handle.get("side", "left")
    handle_height_from_bottom = handle.get("heightFromBottom", 40)

    h_color = HANDLE_COLORS.get(handle_finish, (30, 30, 30))
    h_highlight = tuple(min(255, c + 60) for c in h_color)
    h_shadow = tuple(max(0, c - 15) for c in h_color)

    inset = 5.5  # inches from edge
    handle_x = to_px(inset) - 3 if handle_side == "left" else width_px - to_px(inset) - 3
    handle_center_y = height_px - to_px(handle_height_from_bottom)

    if handle_style == "long-pull":
        # Tall vertical bar ~48" long
        half_h = to_px(24)
        bar_w = max(to_px(0.75), 6)

        # Shadow
        draw.rectangle(
            [handle_x + 3, handle_center_y - half_h + 3,
             handle_x + bar_w + 3, handle_center_y + half_h + 3],
            fill=h_shadow + (100,),
        )
        # Bar
        draw.rectangle(
            [handle_x, handle_center_y - half_h,
             handle_x + bar_w, handle_center_y + half_h],
            fill=h_color,
        )
        # Highlight
        draw.line(
            [(handle_x + 1, handle_center_y - half_h),
             (handle_x + 1, handle_center_y + half_h)],
            fill=h_highlight, width=1,
        )
        # Mounting brackets
        bracket_h = to_px(1.5)
        for by in [handle_center_y - half_h, handle_center_y + half_h - bracket_h]:
            draw.rectangle(
                [handle_x - 2, by, handle_x + bar_w + 2, by + bracket_h],
                fill=h_shadow,
            )

    elif handle_style == "square-pull":
        # Shorter vertical bar ~12" long, thicker
        half_h = to_px(6)
        bar_w = max(to_px(1.0), 8)

        # Shadow
        draw.rectangle(
            [handle_x + 3, handle_center_y - half_h + 3,
             handle_x + bar_w + 3, handle_center_y + half_h + 3],
            fill=h_shadow + (100,),
        )
        # Bar
        draw.rectangle(
            [handle_x, handle_center_y - half_h,
             handle_x + bar_w, handle_center_y + half_h],
            fill=h_color,
        )
        # Highlight
        draw.line(
            [(handle_x + 1, handle_center_y - half_h),
             (handle_x + 1, handle_center_y + half_h)],
            fill=h_highlight, width=1,
        )
        # Top/bottom mounting brackets
        bracket_h = to_px(1.0)
        for by in [handle_center_y - half_h, handle_center_y + half_h - bracket_h]:
            draw.rectangle(
                [handle_x - 2, by, handle_x + bar_w + 2, by + bracket_h],
                fill=h_shadow,
            )

    elif handle_style == "recessed-pull":
        # Flush-mounted recessed groove
        half_h = to_px(4)
        recess_w = max(to_px(1.5), 10)

        recess_color = tuple(max(0, c - 30) for c in blended)
        draw.rectangle(
            [handle_x, handle_center_y - half_h,
             handle_x + recess_w, handle_center_y + half_h],
            fill=recess_color,
        )
        # Inner shadow
        draw.line(
            [(handle_x, handle_center_y - half_h),
             (handle_x + recess_w, handle_center_y - half_h)],
            fill=groove_color, width=2,
        )

    # ── Lighting gradient ─────────────────────────────────────────────

    gradient = Image.new("RGBA", (width_px, height_px), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(gradient)
    for y in range(height_px):
        t = y / height_px
        alpha = int(t * 30)
        grad_draw.line([(0, y), (width_px, y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, gradient)

    # Save
    final = img.convert("RGB")
    final.save(output_path)
    print(f"Door slab rendered: {output_path} ({width_px}x{height_px})")
    return final


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert #RRGGBB to (R, G, B)."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
