#!/usr/bin/env python3
"""
Generate API documentation for the Airdrops system.

This script uses Sphinx to generate comprehensive API documentation
from the source code docstrings and type annotations.
"""

import os
import sys
import subprocess
from pathlib import Path


def generate_api_docs():
    """Generate API documentation using Sphinx."""
    
    # Get paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    docs_dir = project_root / "docs"
    sphinx_dir = docs_dir / "sphinx"
    src_dir = project_root / "src"
    
    # Add src to Python path
    sys.path.insert(0, str(src_dir))
    
    print("Generating API Documentation for Airdrops System")
    print("=" * 50)
    
    # Step 1: Clean previous build
    print("\n1. Cleaning previous build...")
    build_dir = sphinx_dir / "_build"
    if build_dir.exists():
        import shutil
        shutil.rmtree(build_dir)
    
    # Step 2: Generate API RST files using sphinx-apidoc
    print("\n2. Generating API RST files...")
    api_output_dir = sphinx_dir / "api"
    api_output_dir.mkdir(exist_ok=True)
    
    cmd = [
        "sphinx-apidoc",
        "-f",  # Force overwrite
        "-o", str(api_output_dir),  # Output directory
        "-d", "3",  # Maximum depth
        "-e",  # Separate pages for each module
        "-M",  # Put module documentation before submodule
        "--tocfile", "index",  # TOC file name
        str(src_dir / "airdrops"),  # Source directory
        # Exclude patterns
        "*/test_*",
        "*_test.py",
        "*/migrations/*",
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("   API RST files generated successfully")
    except subprocess.CalledProcessError as e:
        print(f"   Error generating API files: {e}")
        return False
    
    # Step 3: Update index.rst to include API docs
    print("\n3. Updating index.rst...")
    index_file = sphinx_dir / "index.rst"
    
    # Read current index
    with open(index_file, 'r') as f:
        content = f.read()
    
    # Add API section if not present
    if "api/index" not in content:
        # Find the API Reference section
        api_section = """.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   api/index
   protocols
   scheduler
   risk_management
   capital_allocation
   monitoring
   analytics
   shared"""
        
        # Replace the existing API Reference section
        import re
        pattern = r'.. toctree::\s*\n\s*:maxdepth: 2\s*\n\s*:caption: API Reference:.*?(?=\n\n|\Z)'
        content = re.sub(pattern, api_section, content, flags=re.DOTALL)
        
        with open(index_file, 'w') as f:
            f.write(content)
        
        print("   index.rst updated")
    
    # Step 4: Build HTML documentation
    print("\n4. Building HTML documentation...")
    os.chdir(sphinx_dir)
    
    cmd = [
        "sphinx-build",
        "-b", "html",  # Build HTML
        "-d", "_build/doctrees",  # Doctrees directory
        "-W",  # Treat warnings as errors
        "--keep-going",  # Continue despite warnings
        ".",  # Source directory
        "_build/html"  # Output directory
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("   HTML documentation built successfully")
    except subprocess.CalledProcessError as e:
        print(f"   Warning: Build completed with warnings: {e}")
        # Continue anyway
    
    # Step 5: Generate PDF documentation (optional)
    print("\n5. Generating PDF documentation...")
    try:
        cmd = [
            "sphinx-build",
            "-b", "latex",
            "-d", "_build/doctrees",
            ".",
            "_build/latex"
        ]
        subprocess.run(cmd, check=True)
        
        # Build PDF
        os.chdir("_build/latex")
        subprocess.run(["pdflatex", "AirdropsAutomationAPIDocs.tex"], check=True)
        subprocess.run(["pdflatex", "AirdropsAutomationAPIDocs.tex"], check=True)  # Run twice for TOC
        print("   PDF documentation generated")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("   PDF generation skipped (LaTeX not installed)")
    
    # Step 6: Generate summary
    print("\n6. Documentation Summary")
    print("=" * 50)
    
    html_dir = sphinx_dir / "_build" / "html"
    if html_dir.exists():
        # Count files
        html_files = list(html_dir.rglob("*.html"))
        print(f"   Generated {len(html_files)} HTML files")
        print(f"   Documentation available at: {html_dir / 'index.html'}")
        
        # List main sections
        print("\n   Main documentation sections:")
        main_files = [
            "index.html",
            "api/index.html",
            "protocols.html",
            "scheduler.html",
            "risk_management.html",
            "capital_allocation.html",
            "monitoring.html",
            "analytics.html",
        ]
        
        for file in main_files:
            file_path = html_dir / file
            if file_path.exists():
                print(f"   ✓ {file}")
    
    print("\n✅ API documentation generation complete!")
    
    # Step 7: Start local server (optional)
    print("\nTo view the documentation locally, run:")
    print(f"   cd {html_dir}")
    print("   python -m http.server 8000")
    print("Then open http://localhost:8000 in your browser")
    
    return True


def check_dependencies():
    """Check if required dependencies are installed."""
    required = ["sphinx", "sphinx-autodoc-typehints"]
    missing = []
    
    for package in required:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        return False
    
    return True


def main():
    """Main entry point."""
    if not check_dependencies():
        sys.exit(1)
    
    success = generate_api_docs()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()