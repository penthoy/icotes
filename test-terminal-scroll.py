#!/usr/bin/env python3
"""
Test script to generate terminal output and verify scrollbar functionality.
This script generates a lot of output to test if the terminal scrollbar is working properly.
"""

import time
import random

def generate_test_output():
    """Generate test output to verify terminal scrollbar functionality."""
    print("🚀 Starting terminal scrollbar test...")
    print("=" * 60)
    
    # Generate numbered lines
    for i in range(1, 101):
        line = f"Line {i:3d}: This is a test line to verify terminal scrollbar functionality"
        if i % 10 == 0:
            line += " 🎯 CHECKPOINT"
        print(line)
        time.sleep(0.05)  # Small delay to make it visible
    
    print("\n" + "=" * 60)
    print("✅ Terminal scrollbar test complete!")
    print("📝 You should see:")
    print("   - A scrollbar on the right side of the terminal")
    print("   - The scrollbar should be visible even when content fits")
    print("   - The terminal should not overflow the bottom boundary")
    print("   - You should be able to scroll through all 100 lines")
    print("=" * 60)

if __name__ == "__main__":
    generate_test_output()
