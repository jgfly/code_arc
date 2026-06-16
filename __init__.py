"""
code_arc - Python Code Architecture Visualizer

Reads a Python project and generates an interactive HTML visualization
showing modules, classes, functions, and their call relationships.
"""

from .analyzer import CodeAnalyzer, PackageInfo
from .generator import HTMLGenerator


def visualize(project_path: str, output_path: str = "code_arc_output.html", title: str | None = None):
    """Analyze a Python project and generate an interactive HTML visualization.

    Args:
        project_path: Path to the Python project root directory.
        output_path: Path for the output HTML file.
        title: Optional title for the visualization. Defaults to project folder name.
    """
    import os
    if title is None:
        title = os.path.basename(os.path.abspath(project_path))

    analyzer = CodeAnalyzer(project_path)
    project_data = analyzer.analyze()

    generator = HTMLGenerator(project_data, title)
    html_content = generator.generate()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"[OK] Visualization generated: {output_path}")
    return output_path


__all__ = ["CodeAnalyzer", "HTMLGenerator", "PackageInfo", "visualize"]
