"""Generate a Acrux app icon set and .icns file."""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


SIZES = [16, 32, 64, 128, 256, 512, 1024]


def draw_acrux_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = size // 16
    radius = size // 8
    box = (pad, pad, size - pad, size - pad)

    # Background gradient simulation: radial from center.
    for y in range(size):
        for x in range(size):
            dx = x - size / 2
            dy = y - size / 2
            dist = math.sqrt(dx * dx + dy * dy) / (size / 2)
            r = int(11 + (26 - 11) * (1 - dist))
            g = int(11 + (26 - 11) * (1 - dist))
            b = int(15 + (46 - 15) * (1 - dist))
            img.putpixel((x, y), (r, g, b, 255))

    # Rounded mask
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(box, radius=radius, fill=255)
    img.putalpha(mask)

    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2

    # Outer glow ring
    ring_r = size * 0.28
    draw.ellipse(
        [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
        outline=(124, 92, 255, 180),
        width=max(2, size // 128),
    )

    # Inner core
    core_r = size * 0.12
    draw.ellipse(
        [cx - core_r, cy - core_r, cx + core_r, cy + core_r],
        fill=(0, 212, 255, 255),
    )
    draw.ellipse(
        [cx - core_r * 0.6, cy - core_r * 0.6, cx + core_r * 0.6, cy + core_r * 0.6],
        fill=(255, 255, 255, 255),
    )

    # Orbital nodes
    node_count = 6
    node_r = max(3, size // 64)
    orbit_r = size * 0.34
    nodes = []
    for i in range(node_count):
        angle = (i / node_count) * 2 * math.pi + 0.3
        nx = cx + math.cos(angle) * orbit_r
        ny = cy + math.sin(angle) * orbit_r
        nodes.append((nx, ny))
        draw.ellipse(
            [nx - node_r, ny - node_r, nx + node_r, ny + node_r],
            fill=(124, 92, 255, 255),
        )

    # Connections between nodes and core
    for nx, ny in nodes:
        draw.line([(cx, cy), (nx, ny)], fill=(124, 92, 255, 90), width=max(1, size // 256))
    for i in range(node_count):
        x1, y1 = nodes[i]
        x2, y2 = nodes[(i + 1) % node_count]
        draw.line([(x1, y1), (x2, y2)], fill=(124, 92, 255, 60), width=max(1, size // 256))

    return img


def generate_icns(output_path: Path) -> None:
    output_path = output_path.resolve()
    iconset = output_path.parent / "Acrux.iconset"
    iconset.mkdir(parents=True, exist_ok=True)

    for size in SIZES:
        icon = draw_acrux_icon(size)
        icon.save(iconset / f"icon_{size}x{size}.png")
        if size <= 512:
            icon2x = draw_acrux_icon(size * 2)
            icon2x.save(iconset / f"icon_{size}x{size}@2x.png")

    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(output_path)], check=True)


if __name__ == "__main__":
    out = Path(__file__).parent / "Acrux.app" / "Contents" / "Resources" / "Acrux.icns"
    out.parent.mkdir(parents=True, exist_ok=True)
    generate_icns(out)
    print(f"Generated {out}")
