#!/usr/bin/env python3
"""
Visual Regression & Quality Audit for DARI Tenancy Contract Generator
Compares generated pages 1-9 against official reference demo pages.
"""

import os
import sys
import numpy as np
from PIL import Image, ImageChops

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEMO_DIR = os.path.join(BASE_DIR, "demo")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "202401452705")
COMPARE_DIR = os.path.join(BASE_DIR, "comparison")

os.makedirs(COMPARE_DIR, exist_ok=True)

def audit_pages():
    print(f"{'Page':<6} | {'Resolution':<12} | {'Mean Pixel Diff':<16} | {'Max Diff':<10} | {'Status'}")
    print("-" * 65)

    all_passed = True
    for p in range(1, 10):
        demo_file = os.path.join(DEMO_DIR, f"{p}.png")
        gen_file = os.path.join(OUTPUT_DIR, f"{p}.png")

        if not os.path.exists(gen_file):
            print(f"Page {p}: Generated file not found: {gen_file}")
            all_passed = False
            continue

        im_demo = Image.open(demo_file).convert("RGB")
        im_gen = Image.open(gen_file).convert("RGB")

        arr_demo = np.array(im_demo, dtype=int)
        arr_gen = np.array(im_gen, dtype=int)

        diff = np.abs(arr_demo - arr_gen)
        mean_diff = np.mean(diff)
        max_diff = np.max(diff)

        # Generate side-by-side comparison thumbnail for visual audit (width 707x1000 each)
        thumb_demo = im_demo.resize((707, 1000), Image.Resampling.LANCZOS)
        thumb_gen = im_gen.resize((707, 1000), Image.Resampling.LANCZOS)

        side_by_side = Image.new("RGB", (707 * 2 + 10, 1000), (220, 220, 220))
        side_by_side.paste(thumb_demo, (0, 0))
        side_by_side.paste(thumb_gen, (707 + 10, 0))
        side_by_side.save(os.path.join(COMPARE_DIR, f"compare_page_{p}.png"))

        status = "EXCELLENT" if mean_diff < 12.0 else ("GOOD" if mean_diff < 25.0 else "REVIEW")
        print(f"Page {p:<2} | {im_gen.size[0]}x{im_gen.size[1]}   | {mean_diff:<16.2f} | {max_diff:<10} | {status}")

    print("-" * 65)
    print(f"Side-by-side visual audits saved to: {COMPARE_DIR}/compare_page_1.png through 9.png")
    return all_passed

if __name__ == "__main__":
    audit_pages()
