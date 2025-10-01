"""
Test entrypoint script for icpy CLI.

This shim imports the real CLI and executes its main() so integration tests
can invoke it as a standalone script without depending on package execution.
"""

import sys
import os


def main():
    # Ensure backend package root is importable when run as a script
    here = os.path.dirname(os.path.abspath(__file__))
    backend_root = os.path.dirname(here)
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    try:
        from icpy.cli.icpy_cli import main as icpy_main
    except ModuleNotFoundError:
        # Fallback: add project root two levels up
        project_root = os.path.dirname(backend_root)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from icpy.cli.icpy_cli import main as icpy_main
    return icpy_main()


if __name__ == "__main__":
    sys.exit(main())
