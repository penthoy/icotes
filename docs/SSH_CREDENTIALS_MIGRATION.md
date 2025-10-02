# SSH Credentials Storage Migration

## Overview
SSH credentials have been migrated from `~/.icotes/ssh/` to `workspace/.icotes/ssh/` for Docker container persistence.

## Why This Change?
- **Docker compatibility**: Home directory (`~/.icotes`) is not persisted in Docker containers
- **Workspace volumes**: The `workspace/` directory is mounted as a volume and survives container restarts
- **Portability**: Credentials travel with the workspace, useful for team setups with shared credentials

## New Storage Location

### Before (Home Directory):
```
~/.icotes/ssh/
├── credentials.json
└── keys/
    └── {uuid}
```

### After (Workspace):
```
workspace/.icotes/ssh/
├── credentials.json
└── keys/
    └── {uuid}
```

## Migration Steps

If you have existing credentials in `~/.icotes/ssh/`, migrate them with:

```bash
# Create the new directory structure
mkdir -p workspace/.icotes/ssh/keys
chmod 700 workspace/.icotes/ssh

# Copy credentials file
cp ~/.icotes/ssh/credentials.json workspace/.icotes/ssh/

# Copy all private keys (preserves permissions)
cp -p ~/.icotes/ssh/keys/* workspace/.icotes/ssh/keys/

# Verify the migration
ls -la workspace/.icotes/ssh/
ls -l workspace/.icotes/ssh/keys/

# Optional: Backup old credentials
mv ~/.icotes/ssh ~/.icotes/ssh.backup
```

## Security

- Directory permissions: `drwx------ (700)` - only owner can access
- Private key permissions: `-rw------- (600)` - only owner can read/write
- Passwords/passphrases are **never** persisted (write-only in memory)
- `.gitignore` updated to exclude `workspace/.icotes/ssh/`

## Code Changes

### Updated in `backend/icpy/services/hop_service.py`:

1. **_app_data_dir()** now resolves workspace root and returns `workspace/.icotes/ssh/`
2. Uses same workspace resolution logic as `filesystem_service.py` and `chat_service.py`
3. Falls back to Docker paths (`/app/workspace`) when needed

### Workspace Resolution Order:
1. `WORKSPACE_ROOT` environment variable
2. Search upwards for parent containing `workspace/` directory
3. Docker fallback: `/app/workspace` if exists
4. Last resort: `$(pwd)/workspace`

## Testing

After migration, test by:

1. Restart the backend service
2. Open the Hop panel in UI
3. Verify your saved credentials appear
4. Test connecting to a saved credential
5. Verify terminal and file operations work

## Docker Usage

In Docker, the workspace is typically mounted as:
```yaml
volumes:
  - ./workspace:/app/workspace
```

With this change, credentials will persist across container restarts.

## Rollback

If needed, you can restore the old behavior by reverting the changes to `_app_data_dir()` in `hop_service.py`.
