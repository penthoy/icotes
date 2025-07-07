# Changelog

All notable changes to the JavaScript Code Editor project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Real terminal with PTY support using xterm.js and WebSocket communication
- Python language support as default with syntax highlighting
- VSCode-like file explorer sidebar with resizable panel
- FastAPI backend with WebSocket support for real-time communication
- Flexible UI panel system with collapse/expand and maximize functionality
- Multi-tab terminal system with closable tabs
- Vertical resizable terminal/output panel
- Comprehensive system architecture documentation

### Fixed
- Terminal connection and WebSocket communication issues
- Terminal boundary detection and scrolling problems
- Panel disappearing when arrow buttons are clicked
- Cursor disappearing issue in code editor
- Output panel layout positioning
- Frontend-backend connection problems
- Production frontend serving and static file handling
- Development environment script consistency

### Changed
- Updated development script to single-port architecture
- Enhanced port configuration for flexible deployment
- Improved terminal layout and scrolling behavior
- Streamlined deployment process with unified port usage

### Removed
- Tempo-specific code and dependencies cleanup
- Unused development artifacts and configurations

---
*Last updated: July 7, 2025*
