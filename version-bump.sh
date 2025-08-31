#!/bin/bash
# Version management script for icotes
# Usage: ./version-bump.sh [patch|minor|major]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get current version
CURRENT_VERSION=$(node -p "require('./package.json').version")
echo -e "${BLUE}Current version: ${CURRENT_VERSION}${NC}"

# Determine bump type
BUMP_TYPE=${1:-patch}
if [[ ! "$BUMP_TYPE" =~ ^(patch|minor|major)$ ]]; then
    echo -e "${RED}Error: Bump type must be patch, minor, or major${NC}"
    echo "Usage: $0 [patch|minor|major]"
    exit 1
fi

echo -e "${YELLOW}Bumping ${BUMP_TYPE} version...${NC}"

# Bump version using npm
npm version $BUMP_TYPE --no-git-tag-version

# Get new version
NEW_VERSION=$(node -p "require('./package.json').version")
echo -e "${GREEN}New version: ${NEW_VERSION}${NC}"

# Check if we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "main" ]]; then
    echo -e "${YELLOW}Warning: You're on branch '${CURRENT_BRANCH}', not 'main'${NC}"
    echo -e "${YELLOW}The Docker build workflow only runs on main branch${NC}"
    echo ""
    echo -e "${BLUE}Options:${NC}"
    echo "1. Push to current branch and create PR to main"
    echo "2. Switch to main branch and cherry-pick this change"
    echo ""
fi

# Stage the change
git add package.json

# Show what will be committed
echo -e "${BLUE}Files staged for commit:${NC}"
git diff --cached --name-only

echo ""
echo -e "${BLUE}Commit and push? (y/N)${NC}"
read -r CONFIRM

if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
    # Commit the version bump
    git commit -m "bump version to ${NEW_VERSION}

    - Updated package.json version from ${CURRENT_VERSION} to ${NEW_VERSION}
    - This will trigger Docker build workflow when merged to main"
    
    echo -e "${GREEN}✅ Committed version bump${NC}"
    
    # Push to current branch
    git push
    echo -e "${GREEN}✅ Pushed to ${CURRENT_BRANCH}${NC}"
    
    if [[ "$CURRENT_BRANCH" == "main" ]]; then
        echo -e "${GREEN}🚀 Docker build workflow will start automatically!${NC}"
        echo -e "${BLUE}Monitor progress at: https://github.com/penthoy/icotes/actions${NC}"
    else
        echo -e "${YELLOW}📋 Create PR to main to trigger Docker build workflow${NC}"
        echo -e "${BLUE}PR Link: https://github.com/penthoy/icotes/compare/main...${CURRENT_BRANCH}${NC}"
    fi
else
    echo -e "${YELLOW}Version bumped but not committed. Run the following when ready:${NC}"
    echo "  git commit -m 'bump version to ${NEW_VERSION}'"
    echo "  git push"
fi

echo ""
echo -e "${BLUE}Version Management Summary:${NC}"
echo -e "  Old: ${CURRENT_VERSION}"
echo -e "  New: ${NEW_VERSION}"
echo -e "  Type: ${BUMP_TYPE}"
echo -e "  Branch: ${CURRENT_BRANCH}"
