#!/usr/bin/env python3
"""
code_arc - Python Code Architecture Visualizer

Usage:
    python -m code_arc <project_path> [output.html]

Examples:
    python -m code_arc ./my_project
    python -m code_arc ./my_project visualization.html
"""

import sys
from . import visualize


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m code_arc <project_path> [output.html]")
        print("")
        print("Arguments:")
        print("  project_path  Path to the Python project directory")
        print("  output.html   Output HTML file path (default: code_arc_output.html)")
        sys.exit(1)

    project_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "code_arc_output.html"

    visualize(project_path, output_path)


if __name__ == "__main__":
    main()
