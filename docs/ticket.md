# ICPY Backend Issue Ticket

**Issue Type:** Backend Error  
**Priority:** High  
**Status:** Open  
**Date Created:** July 19, 2025  

## Issue Summary
ICPY REST API `/api/files` endpoint is returning 500 Internal Server Error when attempting to save files via PUT requests.

## Error Details
- **HTTP Status:** 500 Internal Server Error
- **Endpoint:** PUT `/api/files`
- **Backend Server:** Running on port 8000
- **Error Source:** ICPY REST API layer

## How to Reproduce
1. Start the ICPY backend server (ensure it's running with venv)
2. Backend should be accessible at `http://192.168.2.195:8000` or configured backend URL
3. Send a PUT request to `/api/files` with the following payload:
   ```json
   {
     "path": "/home/penthoy/ilaborcode/workspace/test.py",
     "content": "# Test file content\nprint('Hello World')",
     "encoding": "utf-8",
     "create_dirs": true
   }
   ```
4. **Expected Result:** 200 OK with success response
5. **Actual Result:** 500 Internal Server Error

## Curl Command to Reproduce
```bash
curl -X PUT http://192.168.2.195:8000/api/files \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/home/penthoy/ilaborcode/workspace/test.py",
    "content": "# Test file content\nprint(\"Hello World\")",
    "encoding": "utf-8",
    "create_dirs": true
  }'
```

## Backend Log Evidence
From the terminal logs, we can see:
```
INFO:icpy.api.rest_api:PUT /api/files - 500 - 0.001s
ERROR:icpy.api.rest_api:Error updating file: FileSystemService.write_file() got an unexpected keyword argument 'path'
```

## Root Cause Analysis
The error indicates that the `FileSystemService.write_file()` method is receiving an unexpected keyword argument `path`. This suggests:

1. **API Contract Mismatch:** The REST API is passing parameters that don't match the FileSystemService method signature
2. **Parameter Name Issue:** The method might expect a different parameter name (e.g., `file_path`, `filepath`, etc.)
3. **Method Signature Change:** The FileSystemService.write_file() method signature may have changed without updating the REST API layer

## Working Endpoints (for reference)
These endpoints are working correctly:
- GET `/health` - Returns healthy status
- GET `/api/files?path=...` - Lists files successfully  
- GET `/api/files/content?path=...` - Retrieves file content successfully

## Files Involved
- **REST API Layer:** `/icpy/api/` (file save endpoint)
- **FileSystemService:** Core file writing service
- **Frontend Client:** `EditorBackendClient.saveFile()` in `/tests/integration/simpleeditor.tsx`

## Expected Fix
Update the ICPY REST API `/api/files` PUT endpoint to:
1. Use correct parameter names when calling `FileSystemService.write_file()`
2. Ensure parameter mapping matches the service method signature
3. Add proper error handling and logging
4. Return appropriate success/error responses

## Testing Requirements
After fix, verify:
1. PUT `/api/files` returns 200 OK for valid requests
2. Files are actually written to the filesystem
3. Error responses include meaningful error messages
4. Frontend SimpleEditor save functionality works end-to-end

## Additional Context
- **Environment:** Development setup with venv
- **Backend Framework:** FastAPI with ICPY services
- **Frontend:** React TypeScript application
- **File Operations:** Writing to `/home/penthoy/ilaborcode/workspace/` directory

## Contact
Frontend integration is ready - this is purely a backend API issue that needs ICPY developer attention.
