# Testing Checklist: WebSocket Streaming Optimization

## ✅ Pre-Testing Setup

- [ ] Backend running: `cd backend && uv run python main.py`
- [ ] Frontend running: `npm run dev`
- [ ] Chrome DevTools open (Console + Network tabs)

## ✅ Test Cases

### 1. Basic Image Generation
- [ ] Open chat interface
- [ ] Send message: "generate an image of a red square"
- [ ] **Expected**: Image appears quickly
- [ ] **Verify**: No Chrome violations in Console

### 2. Performance Validation
**Chrome DevTools Console:**
- [ ] No "[Violation] 'message' handler took" warnings
- [ ] Message handler completes in <10ms

**Network Tab:**
- [ ] WebSocket message size: ~2KB (not 200KB)
- [ ] Separate HTTP GET for `/api/media/image/{id}`
- [ ] Image request has Cache-Control header (max-age=31536000)

### 3. Image Display
- [ ] Thumbnail appears instantly (<50ms)
- [ ] Full image loads separately (if different)
- [ ] Image is clear and high-quality
- [ ] No visible loading delays or jank

### 4. Download Functionality
- [ ] Click download button on image widget
- [ ] Image downloads successfully
- [ ] Downloaded image is full resolution (not thumbnail)
- [ ] Filename format: `generated-image-{timestamp}.png`

### 5. Copy URL
- [ ] Click "Copy URL" on image widget
- [ ] URL copied to clipboard
- [ ] Format: `/api/media/image/{image_id}`
- [ ] Pasting URL in browser serves the image

### 6. Multiple Images
- [ ] Generate 3-5 images in sequence
- [ ] **Verify**: No performance degradation
- [ ] **Verify**: No Chrome violations
- [ ] **Verify**: Each image has unique ID
- [ ] **Verify**: Browser caches images (check Network tab)

### 7. Backward Compatibility
- [ ] Load chat with old messages (if available)
- [ ] **Verify**: Old images still display correctly
- [ ] **Verify**: No errors in console
- [ ] **Verify**: Legacy format gracefully handled

### 8. Error Handling
- [ ] Try generating image with invalid prompt (if applicable)
- [ ] **Verify**: Error displayed clearly
- [ ] **Verify**: No console errors
- [ ] **Verify**: UI remains responsive

### 9. Image Reference API
**Test endpoint directly:**
```bash
# Get image by ID (from previous generation)
curl http://localhost:8000/api/media/image/{IMAGE_ID} -o test.png

# Get thumbnail
curl http://localhost:8000/api/media/image/{IMAGE_ID}?thumbnail=true -o thumb.jpg
```
- [ ] Full image downloads correctly
- [ ] Thumbnail downloads correctly
- [ ] Headers include Cache-Control
- [ ] Response includes X-Image-Source header

### 10. Automated Test
```bash
cd /home/penthoy/icotes/backend
uv run pytest tests/manual/test_streaming_optimization.py -v -s
```
- [ ] Test passes
- [ ] JSON size < 100KB
- [ ] Size reduction ~99%
- [ ] Thumbnail size < 20KB

## ✅ Performance Benchmarks

Record these metrics for comparison:

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| WebSocket message size | <10KB | _____ | ☐ |
| JSON parse time | <10ms | _____ | ☐ |
| Thumbnail display | <50ms | _____ | ☐ |
| Full image load | <500ms | _____ | ☐ |
| Chrome violations | 0 | _____ | ☐ |

## ✅ Browser Cache Validation

1. Generate an image
2. Note the image ID
3. Reload the page
4. Open Network tab, filter by image ID
5. **Verify**: Second load shows "(disk cache)" or "304 Not Modified"

## ✅ Known Issues / Edge Cases

- [ ] Large images (>5MB) load without issues
- [ ] Multiple concurrent generations work correctly
- [ ] Image editing/regeneration works
- [ ] Hop (remote) contexts work (if applicable)
- [ ] Mobile browsers display correctly

## ✅ Rollback Plan

If issues occur:

1. **Disable new format**:
   ```python
   # In imagen_tool.py, temporarily revert to:
   result_data = {
       "imageData": raw_base64,  # Legacy format
       "imageUrl": image_data_uri,
       # ...
   }
   ```

2. **Frontend graceful degradation**:
   - Widget already has fallback for legacy format
   - No code changes needed on frontend

3. **Restart services**:
   ```bash
   # Backend
   cd backend && uv run python main.py
   
   # Frontend
   npm run dev
   ```

## ✅ Success Criteria

All must be ✓ to consider optimization successful:

- ✓ No Chrome performance violations
- ✓ WebSocket messages <10KB
- ✓ Images display correctly
- ✓ Download works
- ✓ Browser caching works
- ✓ Automated test passes
- ✓ Backward compatible

## ✅ Sign-Off

- [ ] Developer tested: _________________ Date: _______
- [ ] QA tested: _________________ Date: _______
- [ ] Performance validated: _________________ Date: _______
- [ ] Ready for production: ☐ Yes ☐ No

## Notes

_Add any observations, issues, or additional testing results here:_

---

**Reference Documents**:
- Implementation: `docs/features/streaming-optimization.md`
- Diagram: `docs/features/streaming-optimization-diagram.txt`
- Summary: `docs/features/streaming-optimization-summary.md`
