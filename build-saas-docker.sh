#!/usr/bin/env bash
set -euo pipefail

# Build SaaS-mode enabled image for icotes and tag as penthoy/icotes_saas:latest
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
GIT_COMMIT="$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo local)"
IMAGE_TAG="${1:-penthoy/icotes_saas:latest}"

export DOCKER_BUILDKIT=1

echo "🔨 Building SaaS-enabled Docker image..."
echo "📦 Tag: $IMAGE_TAG"
echo "🗓️  Build date: $BUILD_DATE"
echo "📝 Git commit: $GIT_COMMIT"
echo ""

docker build \
  -f "$REPO_DIR/Dockerfile" \
  --build-arg BUILD_VERSION="saas-$(date +%Y%m%d)" \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  --build-arg GIT_COMMIT="$GIT_COMMIT" \
  -t "$IMAGE_TAG" \
  "$REPO_DIR"

echo ""
echo "✅ Successfully built SaaS-enabled Docker image: $IMAGE_TAG"
echo ""
echo "🧪 To test SaaS mode locally:"
echo "   docker run -p 8000:8000 \\"
echo "     -e AUTH_MODE=saas \\"
echo "     -e SUPABASE_JWT_SECRET=test-secret-key \\"
echo "     -e UNAUTH_REDIRECT_URL=https://icotes.com \\"
echo "     $IMAGE_TAG"
echo ""
echo "🧪 To test standalone mode locally:"
echo "   docker run -p 8000:8000 $IMAGE_TAG"
