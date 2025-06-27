#!/usr/bin/env python3
"""
Script to run code quality checks on ALL files (including untracked).
This goes beyond pre-commit's git-tracked file limitation.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n🔍 {description}")
    print("-" * 60)

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")

        return result.returncode == 0

    except Exception as e:
        print(f"💥 Error running {description}: {e}")
        return False


def main():
    """Run all code quality checks on all files."""
    project_root = Path(__file__).parent.parent

    print("🚀 Running comprehensive code quality checks on ALL files")
    print(f"📁 Project root: {project_root}")

    # Change to project directory
    import os

    os.chdir(project_root)

    checks = [
        # Formatting checks
        ("black . --check --diff", "Black formatting check"),
        ("isort . --check-only --diff", "Import sorting check"),
        # Linting checks
        ("flake8 .", "Flake8 linting"),
        ("mypy .", "MyPy type checking"),
        ("bandit -r . -f json", "Bandit security check"),
        # File checks
        (
            "find . -name '*.py' -exec python -m py_compile {} \\;",
            "Python syntax check",
        ),
    ]

    results = []

    for cmd, description in checks:
        success = run_command(cmd, description)
        results.append((description, success))

    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status:12} {description}")

    print(f"\n🎯 Overall: {passed}/{total} checks passed")

    if passed == total:
        print("🎉 All checks passed!")
        return 0
    else:
        print("🔧 Some checks failed - review output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
