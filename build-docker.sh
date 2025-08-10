#!/bin/bash
set -e

# Build script for iCotes Docker image
VERSION="${1:-1.0.3}"
IMAGE_NAME="penthoy/icotes"
FULL_TAG="${IMAGE_NAME}:${VERSION}"

echo "🐳 Building iCotes Docker image..."
echo "📦 Version: ${VERSION}"
echo "🏷️  Tag: ${FULL_TAG}"
echo ""

# Build the Docker image
echo "🔨 Building Docker image..."
docker build \
  --build-arg BUILD_VERSION="${VERSION}" \
  --build-arg BUILD_DATE="$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
  --build-arg GIT_COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')" \
  -t "${FULL_TAG}" \
  -t "${IMAGE_NAME}:latest" \
  .

echo ""
echo "✅ Docker image built successfully!"
echo "🏷️  Tags created:"
echo "   - ${FULL_TAG}"
echo "   - ${IMAGE_NAME}:latest"

# Show image size
echo ""
echo "📊 Image size:"
docker images "${IMAGE_NAME}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

echo ""
echo "🚀 To push to registry:"
echo "   docker push ${FULL_TAG}"
echo "   docker push ${IMAGE_NAME}:latest"

echo ""
echo "🧪 To test locally:"
echo "   docker run -p 8000:8000 ${FULL_TAG}"
