# Docker Build Workflow Setup Instructions

## 🚀 Automated Docker Build & Deploy Workflow

I've created a comprehensive GitHub Actions workflow that will automatically build and push your Docker images whenever the main branch is updated with a new version.

## 📋 How It Works

### Triggers
- **Push to main branch**: Builds immediately when code is pushed to main
- **PR merge to main**: Builds when a pull request is merged into main

### Smart Version Detection
- Reads version from `package.json`
- Only builds if the version is new (doesn't already exist as a Git tag)
- Skips build if version hasn't changed to save resources

### What It Builds
1. **Main Docker Image**: `penthoy/icotes:1.5.6` and `penthoy/icotes:latest`
2. **SaaS Docker Image**: `penthoy/icotes_saas:1.5.6` and `penthoy/icotes_saas:latest`

## 🔧 Setup Required

### 1. Add Docker Hub Secrets
You need to add these secrets to your GitHub repository:

**Go to**: `https://github.com/penthoy/icotes/settings/secrets/actions`

**Add these secrets**:
- `DOCKER_USERNAME`: Your Docker Hub username (`penthoy`)
- `DOCKER_PASSWORD`: Your Docker Hub password or access token

### 2. Ensure Docker Hub Repository Exists
Make sure these repositories exist on Docker Hub:
- `penthoy/icotes`
- `penthoy/icotes_saas`

## 📝 Workflow Features

### ✅ What It Does
- **Version Detection**: Automatically extracts version from `package.json`
- **Build Optimization**: Only builds when version changes
- **Dual Image Build**: Creates both main and SaaS images
- **Registry Push**: Pushes to Docker Hub with version and latest tags
- **Git Tagging**: Creates `v1.5.6` style tags for releases
- **GitHub Releases**: Auto-creates releases with Docker usage instructions
- **Build Notifications**: Shows clear success/skip/failure messages

### 🎯 Workflow Steps
1. **Check Version**: Extract current version from package.json
2. **Version Validation**: Compare with existing Git tags
3. **Docker Setup**: Configure Docker Buildx and login to Docker Hub
4. **Build Main**: Run `./build/build-docker.sh [version]`
5. **Build SaaS**: Run `./build/build-saas-docker.sh [version]`
6. **Tag Release**: Create Git tag and GitHub release
7. **Notify**: Report build status

## 🚀 How to Trigger

### For New Version
1. Update version in `package.json`:
   ```bash
   # Change version from 1.5.6 to 1.5.7
   npm version patch  # or minor/major
   ```

2. Push to main or merge PR:
   ```bash
   git push origin main
   ```

3. The workflow will:
   - Detect version `1.5.7` is new
   - Build both Docker images
   - Push to Docker Hub
   - Create GitHub release

### For Same Version
- Workflow will detect version hasn't changed
- Skip build process
- Show "Version already exists" message

## 📊 Example Workflow Run

```
✅ Version Check: 1.5.7 (new)
🔨 Building Docker images...
   - penthoy/icotes:1.5.7 ✅
   - penthoy/icotes:latest ✅
   - penthoy/icotes_saas:1.5.7 ✅
   - penthoy/icotes_saas:latest ✅
🏷️  Created tag: v1.5.7
📋 Created GitHub release
🚀 All images pushed to Docker Hub
```

## 🔍 Monitoring

- **GitHub Actions Tab**: See all workflow runs
- **Docker Hub**: Verify images are pushed
- **Releases Tab**: See auto-created releases
- **Tags**: See version tags

## 🛠️ Testing

Once secrets are configured, you can test by:

1. Merging your current branch to main (with version 1.5.6)
2. Or updating to a new version like 1.5.7 and pushing

The workflow will run automatically and you'll see the results in the Actions tab.

## 📁 Files Created
- `.github/workflows/docker-build-deploy.yml` - The main workflow file
