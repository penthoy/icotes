#!/bin/bash
# Clean up Python cache files and other build artifacts

echo "🧹 Cleaning up Python cache files and build artifacts..."

# Remove Python cache files
find . -name "*.pyc" -not -path "./backend/venv/*" -delete
find . -name "__pycache__" -not -path "./backend/venv/*" -exec rm -rf {} + 2>/dev/null || true

# Remove Python build artifacts
find . -name "*.pyo" -not -path "./backend/venv/*" -delete
find . -name "*.pyd" -not -path "./backend/venv/*" -delete
find . -name "*.so" -not -path "./backend/venv/*" -delete
find . -name "*.egg-info" -not -path "./backend/venv/*" -exec rm -rf {} + 2>/dev/null || true

# Remove Node.js cache files
rm -rf node_modules/.cache/
rm -rf .npm/

# Remove build directories (but not the dist from git)
rm -rf backend/build/
rm -rf backend/dist/

# Remove log files
rm -f logs/*.log
rm -f *.log

# Remove temporary files
find . -name "*.tmp" -delete
find . -name "*.temp" -delete

# Remove OS-specific files
find . -name ".DS_Store" -delete
find . -name "Thumbs.db" -delete

echo "✅ Cleanup complete!"
echo "📁 The following directories were preserved:"
echo "   - backend/venv/ (Python virtual environment)"
echo "   - node_modules/ (Node.js dependencies)"
echo "   - dist/ (built frontend files)"
