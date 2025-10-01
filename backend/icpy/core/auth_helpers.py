"""
Authentication helper utilities.

Helper functions for SaaS authentication flow including cookie management
and redirect handling.
"""

import os
import logging
from typing import Optional
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from fastapi import Request
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse

logger = logging.getLogger(__name__)

# Excluded paths from authentication checks
EXCLUDED_PATHS = {"healthz", "readiness", "metrics", "favicon.ico"}


def issue_auth_cookie(response: JSONResponse | RedirectResponse, token: str) -> None:
    """Set host-only auth cookie."""
    cookie_name = os.getenv('COOKIE_NAME', 'auth_token')
    # Host-only cookie: do NOT set Domain attribute
    response.set_cookie(
        key=cookie_name,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
        max_age=60 * 60 * 8  # 8 hours default validity; actual token exp governs access
    )


def serve_index_fallback():
    """Serve index.html or a simple fallback without assuming authentication."""
    dist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "dist")
    index_path = os.path.join(dist_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return JSONResponse(content={"message": "icotes backend", "status": "unauthenticated"}, status_code=200)


def get_home_redirect_base() -> str:
    """Compute the home/base URL to send unauthenticated users to (e.g., icotes.com)."""
    # Prefer explicit absolute URL envs
    for key in ["MAIN_SITE_URL", "PUBLIC_HOME_URL", "SITE_HOME_URL", "LOGIN_BASE_URL", "UNAUTH_REDIRECT_URL"]:
        val = os.getenv(key)
        if val and val.startswith("http"):
            return val.rstrip('/')
    # If only a root path was provided, ignore it and build from APP_DOMAIN
    app_domain = os.getenv('APP_DOMAIN', 'icotes.com')
    # Default to https main site
    return f"https://{app_domain}".rstrip('/')


def is_html_route(path: str) -> bool:
    """Check if a path should be treated as an HTML route."""
    # Exclude api/ws and common static paths
    if path.startswith("api/") or path.startswith("ws/"):
        return False
    if path.startswith("assets/") or path.startswith("static/"):
        return False
    if path in EXCLUDED_PATHS:
        return False
    return True


def is_browser_navigation(request: Request) -> bool:
    """Check if request is browser navigation."""
    if request.method.upper() != "GET":
        return False
    accept = (request.headers.get("accept") or "").lower()
    sec_mode = (request.headers.get("sec-fetch-mode") or "").lower()
    # Treat as browser navigation if HTML is acceptable and mode is navigate (or header missing)
    is_html = "text/html" in accept or "*/*" in accept
    is_nav = (sec_mode == "navigate") or (sec_mode == "")
    return is_html and is_nav


def sanitize_return_to(url_str: str) -> Optional[str]:
    """Sanitize return_to URL parameter."""
    try:
        # Updated to support new landing/orchestrator authentication flow
        token_param = os.getenv('TOKEN_QUERY_PARAM', 'token')  # Changed default from 't' to 'token'
        app_domain = os.getenv('APP_DOMAIN', 'icotes.com')
        u = urlparse(url_str)
        # Allow only http/https and enforce host allowlist (app_domain or its subdomains)
        if u.scheme not in ("https", "http"):
            return None
        if app_domain:
            host = (u.hostname or "").lower()
            if not (host == app_domain.lower() or host.endswith("." + app_domain.lower())):
                return None
        # Force https scheme to avoid http→https extra hops
        scheme = "https"
        # Strip sensitive or looping params
        strip_keys = {token_param.lower(), "return_to", "token", "state", "code"}
        q = [(k, v) for (k, v) in parse_qsl(u.query, keep_blank_values=True) if k.lower() not in strip_keys]
        clean = u._replace(scheme=scheme, query=urlencode(q, doseq=True))
        sanitized = urlunparse(clean)
        if len(sanitized) > 2048:
            return None
        return sanitized
    except Exception:
        return None


def build_unauth_redirect(request: Request) -> RedirectResponse:
    """Build redirect for unauthenticated users."""
    # Always send unauthenticated users straight to the main site, not this session subdomain
    base = get_home_redirect_base()
    redirect = RedirectResponse(url=base, status_code=303)
    redirect.headers['Cache-Control'] = 'no-store'
    redirect.headers['X-Robots-Tag'] = 'noindex'
    return redirect