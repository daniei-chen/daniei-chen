#!/usr/bin/env python3
"""Compatibility entry point for the existing scheduled profile workflow.

The coastal artwork is checked in, so daily updates validate it instead of
repainting the old SVG design. tools/make_readme.py handles the public repo index.
"""
from make_readme import validate_assets

if __name__ == "__main__":
    validate_assets()
    print("Coastal artwork verified; original illustrations preserved")
