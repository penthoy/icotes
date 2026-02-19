#!/usr/bin/env python3
"""Convert black background to green for easier keying."""

import numpy as np
from PIL import Image

def black_to_green(image_path, output_path, black_tol=50):
    """Change black/dark background to chroma green."""
    img = Image.open(image_path).convert("RGBA")
    data = np.array(img)
    
    # RGB channels
    rgb = data[:, :, :3].astype(np.float32)
    
    # Detect dark/black pixels (low RGB values)
    brightness = np.mean(rgb, axis=2)
    is_dark = brightness < black_tol
    
    # Also check that R, G, B are all low (not just dark overall)
    all_low = np.all(rgb < black_tol + 30, axis=2)
    is_black_bg = is_dark & all_low
    
    # Replace black background with chroma green
    data[is_black_bg, 0] = 0    # R
    data[is_black_bg, 1] = 255  # G
    data[is_black_bg, 2] = 0    # B
    
    # Keep alpha as is
    
    out = Image.fromarray(data, mode="RGBA")
    out.save(output_path)
    print(f"Converted black background to green: {output_path}")
    print(f"Pixels changed: {np.sum(is_black_bg)}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python black_to_green.py input.png output.png")
        sys.exit(1)
    black_to_green(sys.argv[1], sys.argv[2])
