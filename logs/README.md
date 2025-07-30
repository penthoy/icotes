# Logs Directory

This directory contains all application logs.

## Log Files

- `backend.log` - Backend application logs (from uvicorn/FastAPI)
- `app.log` - Production application logs 
- `*.log` - Various development and debugging logs

## Log Rotation

Production logs are automatically rotated by the system.
Development logs are overwritten on each restart.

## Viewing Logs

```bash
# View backend logs in real-time
tail -f logs/backend.log

# View last 100 lines of backend logs
tail -n 100 logs/backend.log

# Search for errors
grep -i error logs/backend.log
```

## Log Levels

- INFO: General application information
- DEBUG: Detailed debugging information (development only)
- WARNING: Warning messages
- ERROR: Error messages
- CRITICAL: Critical errors
