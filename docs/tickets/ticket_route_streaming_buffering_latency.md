# Ticket: Streaming proxy adds ~4.7s fixed latency — response buffered before forwarding

## Priority: HIGH

## Summary
icotesroute's `/v1/chat/completions` streaming proxy appears to **buffer the entire upstream response before forwarding SSE chunks** to the client, instead of streaming them through in real-time. This adds a consistent ~4.7 second fixed overhead regardless of prompt complexity or upstream response time.

For fast providers like Cerebras (which complete in ~150ms direct), this results in a **28–39x latency penalty**.

---

## Evidence

We profiled direct vs proxy streaming using the OpenAI SDK with `stream=True`, 3 iterations each.

### Test setup
- **Route URL**: `http://192.168.2.202:9100`
- **Provider**: Cerebras (`gpt-oss-120b`) — chose this because it's the fastest provider, making proxy overhead clearly visible
- **Direct endpoint**: `https://api.cerebras.ai/v1`
- **Prompts**: "Say hello" (max_tokens=10), "What is 2+2?" (max_tokens=10)
- **Method**: OpenAI Python SDK, `client.chat.completions.create(stream=True)`, measured wall-clock from request start to last chunk

### Results — Cerebras `gpt-oss-120b`

#### Prompt: "Say hello" (minimal)
| Metric | Direct | Proxy | Overhead |
|--------|--------|-------|----------|
| Connection time (avg) | 551 ms* | 4,815 ms | +4,264 ms |
| Total time (avg) | 588 ms* | 4,824 ms | +4,236 ms |

*\* First-request cold start inflated the direct average; steady-state direct is ~130–165ms.*

#### Prompt: "What is 2+2?" (short)
| Metric | Direct | Proxy | Overhead |
|--------|--------|-------|----------|
| Connection time (avg) | **120 ms** | **4,812 ms** | **+4,692 ms** |
| Total time (avg) | **167 ms** | **4,819 ms** | **+4,652 ms** |

### Raw iteration data (short prompt, steady-state)

| Iteration | Direct total | Proxy total | Proxy connection_ms |
|-----------|-------------|-------------|---------------------|
| 1 | 167 ms | 4,806 ms | 4,799 ms |
| 2 | 203 ms | 4,830 ms | 4,823 ms |
| 3 | 131 ms | 4,819 ms | 4,812 ms |

**Key observation**: The proxy `connection_ms` (time until first byte from proxy) is ~4.8s every single time, regardless of the upstream having responded in ~130ms. The SSE chunks then all arrive in <10ms after the connection opens. This strongly indicates the proxy is:

1. Receiving all SSE chunks from upstream
2. Only then opening the SSE stream to the client
3. Flushing all buffered chunks at once

---

## Expected behavior

The proxy should forward each SSE chunk to the client **as soon as it arrives from upstream**, resulting in:
- `connection_ms` ≈ upstream TTFT + small proxy overhead (~10-50ms)
- Chunk delivery timing matching upstream chunk timing
- Total overhead of ~10-50ms, not ~4,700ms

---

## Suggested fix

In the route's streaming proxy handler, switch from collecting/buffering to passthrough streaming. In FastAPI + httpx this typically looks like:

```python
# BEFORE (buffered — causes the ~4.7s delay):
async def proxy_chat_completions(request):
    response = await httpx_client.post(upstream_url, ...)
    # or: chunks = [chunk async for chunk in response.aiter_lines()]
    return StreamingResponse(iter(chunks), media_type="text/event-stream")

# AFTER (true streaming passthrough):
async def proxy_chat_completions(request):
    upstream_response = await httpx_client.send(
        httpx_client.build_request("POST", upstream_url, ...),
        stream=True
    )

    async def generate():
        async for line in upstream_response.aiter_lines():
            yield line + "\n"
        await upstream_response.aclose()

    return StreamingResponse(generate(), media_type="text/event-stream")
```

Critical points:
- Use `stream=True` on the upstream request so httpx doesn't buffer the body
- Use `aiter_lines()` or `aiter_bytes()` in the async generator — yield each chunk immediately
- Ensure no middleware or response processing is accumulating chunks before forwarding
- Check if there's a response body size or SSE buffering setting that might be collecting data

---

## Reproduction

```bash
# Direct — fast (~150ms)
curl -w "\nTotal: %{time_total}s\nTTFB: %{time_starttransfer}s\n" \
  -X POST https://api.cerebras.ai/v1/chat/completions \
  -H "Authorization: Bearer <CEREBRAS_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-oss-120b","messages":[{"role":"user","content":"Say hello"}],"max_tokens":10,"stream":true}'

# Via route — slow (~4.8s)
curl -w "\nTotal: %{time_total}s\nTTFB: %{time_starttransfer}s\n" \
  -X POST http://192.168.2.202:9100/v1/chat/completions \
  -H "Authorization: Bearer <ROUTE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"model":"cerebras/gpt-oss-120b","messages":[{"role":"user","content":"Say hello"}],"max_tokens":10,"stream":true}'
```

Compare `time_starttransfer` (TTFB) values — the route TTFB will be ~4.8s vs direct ~0.15s.

---

## Impact
- All streaming chat completions through icotesroute have a ~4.7s floor latency
- Fast providers (Cerebras, Groq) are disproportionately affected — their speed advantage is entirely negated
- User-perceived responsiveness is severely degraded — users see no output for ~5s regardless of model speed
- This affects every streaming request, not just edge cases

## Profiler script
Full profiling script with detailed metrics is available at: `backend/tests/profile_icotesroute_latency.py` in the icotes repo. Run with:
```bash
cd backend
uv run python tests/profile_icotesroute_latency.py --cerebras-key <KEY> --iterations 5
```
