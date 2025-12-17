"""Generate Synapse application icon.

Creates a modern icon with a stylized neural/synapse motif.
Outputs multiple sizes embedded in a single .ico file.
"""

import math
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("Pillow is required. Install with: pip install Pillow")
    exit(1)


def create_synapse_icon(size: int) -> Image.Image:
    """Create a single icon image at the specified size.

    Args:
        size: Icon dimension (square)

    Returns:
        PIL Image object
    """
    # Colors from theme
    bg_color = "#1E1E1E"
    accent_color = "#007ACC"
    accent_light = "#1E90FF"
    node_color = "#FFFFFF"

    # Create base image with slight padding for anti-aliasing
    scale = 4  # Supersampling for smoother curves
    canvas_size = size * scale
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded rectangle background
    margin = canvas_size // 16
    corner_radius = canvas_size // 5

    # Background with rounded corners
    draw.rounded_rectangle(
        [margin, margin, canvas_size - margin, canvas_size - margin],
        radius=corner_radius,
        fill=bg_color,
    )

    # Center of the icon
    cx, cy = canvas_size // 2, canvas_size // 2

    # Draw neural network / synapse pattern
    # Central node
    central_radius = canvas_size // 8

    # Outer nodes in a circular pattern
    node_radius = canvas_size // 14
    orbit_radius = canvas_size // 3.2
    num_nodes = 6

    nodes = []
    for i in range(num_nodes):
        angle = (2 * math.pi * i / num_nodes) - math.pi / 2
        x = cx + int(orbit_radius * math.cos(angle))
        y = cy + int(orbit_radius * math.sin(angle))
        nodes.append((x, y))

    # Draw connections (synapses) - gradient effect
    for i, (nx, ny) in enumerate(nodes):
        # Draw connection line with glow effect
        line_width = canvas_size // 24

        # Outer glow
        for glow_width in range(line_width + canvas_size // 16, line_width, -2):
            alpha = int(40 * (1 - (glow_width - line_width) / (canvas_size // 16)))
            glow_color = (*tuple(int(accent_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)), alpha)
            draw.line([(cx, cy), (nx, ny)], fill=glow_color, width=glow_width)

        # Main connection
        draw.line([(cx, cy), (nx, ny)], fill=accent_color, width=line_width)

    # Draw outer nodes
    for nx, ny in nodes:
        # Node glow
        for glow in range(node_radius + canvas_size // 20, node_radius, -2):
            alpha = int(60 * (1 - (glow - node_radius) / (canvas_size // 20)))
            glow_color = (*tuple(int(accent_light.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)), alpha)
            draw.ellipse(
                [nx - glow, ny - glow, nx + glow, ny + glow],
                fill=glow_color,
            )

        # Node fill
        draw.ellipse(
            [nx - node_radius, ny - node_radius, nx + node_radius, ny + node_radius],
            fill=accent_color,
        )

        # Node highlight
        highlight_radius = node_radius // 2
        draw.ellipse(
            [nx - highlight_radius // 2, ny - highlight_radius,
             nx + highlight_radius // 2, ny],
            fill=accent_light,
        )

    # Draw central node (larger, prominent)
    # Central glow
    for glow in range(central_radius + canvas_size // 12, central_radius, -3):
        alpha = int(80 * (1 - (glow - central_radius) / (canvas_size // 12)))
        glow_color = (*tuple(int(accent_light.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)), alpha)
        draw.ellipse(
            [cx - glow, cy - glow, cx + glow, cy + glow],
            fill=glow_color,
        )

    # Central node fill
    draw.ellipse(
        [cx - central_radius, cy - central_radius,
         cx + central_radius, cy + central_radius],
        fill=accent_color,
    )

    # Central node inner highlight
    inner_radius = central_radius * 2 // 3
    draw.ellipse(
        [cx - inner_radius, cy - inner_radius,
         cx + inner_radius, cy + inner_radius],
        fill=accent_light,
    )

    # Add a small "S" in the center for branding
    try:
        # Try to use a system font
        font_size = central_radius
        font = ImageFont.truetype("segoeui.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

    # Draw "S" character
    text = "S"
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = cx - text_width // 2
    text_y = cy - text_height // 2 - bbox[1]

    draw.text((text_x, text_y), text, fill=node_color, font=font)

    # Downsample to target size with high-quality resampling
    img = img.resize((size, size), Image.Resampling.LANCZOS)

    return img


def create_ico_file(output_path: Path) -> None:
    """Create a multi-size .ico file.

    Args:
        output_path: Path to save the .ico file
    """
    # Standard icon sizes for Windows
    sizes = [256, 128, 64, 48, 32, 16]

    images = []
    for size in sizes:
        print(f"  Generating {size}x{size} icon...")
        img = create_synapse_icon(size)
        images.append(img)

    # Save as ICO with all sizes
    images[0].save(
        output_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )

    print(f"Icon saved to: {output_path}")


def main():
    """Generate the Synapse icon."""
    # Determine output path
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    output_path = project_dir / "synapse" / "assets" / "synapse.ico"

    print("Generating Synapse icon...")
    create_ico_file(output_path)

    # Also save a PNG for other uses
    png_path = output_path.with_suffix(".png")
    icon_256 = create_synapse_icon(256)
    icon_256.save(png_path, format="PNG")
    print(f"PNG version saved to: {png_path}")


if __name__ == "__main__":
    main()
