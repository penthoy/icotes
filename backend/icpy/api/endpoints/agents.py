"""
Custom agents API endpoints.

These endpoints handle custom agent management, reloading, and execution.
"""

import os
import re
import logging
import time
import tempfile
import contextlib
from typing import Dict, Any

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

try:
    from icpy.agent.custom_agent import (
        get_available_custom_agents, get_configured_custom_agents,
        reload_custom_agents, reload_agent_environment, get_agent_info
    )
    from icpy.services.agent_config_service import get_agent_config_service
    from icpy.auth import auth_manager, get_optional_user
    ICPY_AVAILABLE = True
except ImportError:
    logger.warning("icpy custom agent modules not available")
    ICPY_AVAILABLE = False
    get_available_custom_agents = lambda: ["TestAgent", "DefaultAgent"]
    get_configured_custom_agents = lambda: []
    reload_custom_agents = lambda: []
    reload_agent_environment = lambda: False
    get_agent_info = lambda name: {}
    get_agent_config_service = lambda: None
    auth_manager = None
    get_optional_user = lambda request: None


async def get_custom_agents():
    """Get list of available custom agents for frontend dropdown menu."""
    try:
        logger.info("Custom agents endpoint called")
        agents = get_available_custom_agents()
        logger.info(f"Retrieved custom agents: {agents}")
        return {"success": True, "agents": agents}
    except ImportError as e:
        logger.warning(f"icpy custom agent module not available: {e}")
        # Fallback: return some default agents for testing
        fallback_agents = ["AgentCreator", "OpenAIDemoAgent", "TestAgent", "DefaultAgent"]
        return {"success": True, "agents": fallback_agents}
    except Exception as e:
        logger.error(f"Error getting custom agents: {e}")
        return {"success": False, "error": str(e), "agents": []}


async def get_configured_custom_agents():
    """Get list of custom agents with their display configuration from workspace."""
    try:
        logger.info("Configured custom agents endpoint called")
        
        # Import the actual function to avoid naming conflict
        from icpy.agent.custom_agent import get_configured_custom_agents as get_configured_agents_impl
        configured_agents = get_configured_agents_impl()
        logger.info(f"Retrieved {len(configured_agents)} configured agents")
        
        # Also get settings and categories including default agent
        config_service = get_agent_config_service()
        config = config_service.load_config() if config_service else {}
        settings = config.get("settings", {})
        categories = config.get("categories", {})
        
        return {
            "success": True, 
            "agents": configured_agents,
            "settings": settings,
            "categories": categories,
            "message": f"Retrieved {len(configured_agents)} configured agents"
        }
    except ImportError as e:
        logger.warning(f"Agent config service not available: {e}")
        # Fallback to basic agent list
        agents = get_available_custom_agents()
        fallback_agents = [
            {"name": agent, "displayName": agent, "description": "", "category": "General", "order": 999, "icon": "🤖"} 
            for agent in agents
        ]
        return {"success": True, "agents": fallback_agents}
    except Exception as e:
        logger.error(f"Error getting configured custom agents: {e}")
        return {"success": False, "error": str(e), "agents": []}


async def reload_custom_agents_endpoint(request: Request):
    """Reload all custom agents and return updated list."""
    try:
        # Check authentication in SaaS mode
        if auth_manager and auth_manager.is_saas_mode():
            user = get_optional_user(request)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            # TODO: Add admin role check if needed
            logger.info(f"Agent reload requested by user: {user.get('sub', 'unknown')}")
        else:
            logger.info("Agent reload requested in standalone mode")
        
        # Perform reload
        reloaded_agents = await reload_custom_agents()
        
        logger.info(f"Agent reload complete. Available agents: {reloaded_agents}")
        
        # Send WebSocket notification to connected clients
        try:
            if ICPY_AVAILABLE:
                # Lazy import to avoid startup errors when messaging is unavailable
                from icpy.core.message_broker import get_message_broker
                message_broker = await get_message_broker()
                await message_broker.publish(
                    topic="agents.reloaded",
                    payload={
                        "type": "agents_reloaded",
                        "agents": reloaded_agents,
                        "timestamp": time.time(),
                        "message": f"Reloaded {len(reloaded_agents)} agents"
                    }
                )
                logger.info("WebSocket notification sent for agent reload")
        except Exception as e:
            logger.warning(f"Failed to send WebSocket notification: {e}")
        
        return {"success": True, "agents": reloaded_agents, "message": f"Reloaded {len(reloaded_agents)} agents"}
        
    except ImportError as e:
        logger.error(f"Hot reload system not available: {e}")
        return {"success": False, "error": "Hot reload system not available", "agents": []}
    except HTTPException:
        raise  # Re-raise HTTP exceptions (like 401)
    except Exception as e:
        logger.error(f"Error reloading custom agents: {e}")
        return {"success": False, "error": str(e), "agents": []}


async def reload_environment_endpoint(request: Request):
    """Reload environment variables for all agents."""
    try:
        # Check authentication in SaaS mode
        if auth_manager and auth_manager.is_saas_mode():
            user = get_optional_user(request)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            logger.info(f"Environment reload requested by user: {user.get('sub', 'unknown')}")
        else:
            logger.info("Environment reload requested in standalone mode")
        
        # Perform environment reload
        success = await reload_agent_environment()
        
        if success:
            logger.info("Environment reload successful")
            return {"success": True, "message": "Environment variables reloaded successfully"}
        else:
            logger.warning("Environment reload failed")
            return {"success": False, "error": "Environment reload failed"}
            
    except ImportError as e:
        logger.error(f"Hot reload system not available: {e}")
        return {"success": False, "error": "Hot reload system not available"}
    except HTTPException:
        raise  # Re-raise HTTP exceptions (like 401)
    except Exception as e:
        logger.error(f"Error reloading environment: {e}")
        return {"success": False, "error": str(e)}


async def update_api_keys_endpoint(request: Request):
    """Update environment variables (API keys and settings) with hot reload and persistence."""
    try:
        # Check authentication in SaaS mode
        if auth_manager and auth_manager.is_saas_mode():
            user = get_optional_user(request)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            logger.info(f"Environment settings update requested by user: {user.get('sub', 'unknown')}")
        else:
            logger.info("Environment settings update requested in standalone mode")
        
        # Get request body
        body = await request.json()
        api_keys = body.get('api_keys', {})
        
        if not api_keys:
            return {"success": False, "error": "No environment settings provided"}

        allowed_keys = {
            # Site settings
            'SITE_URL',
            'WORKSPACE_ROOT',
            'PORT',
            # AI keys / providers
            'OPENROUTER_API_KEY',
            'OPENAI_API_KEY',
            'ANTHROPIC_API_KEY',
            'GOOGLE_API_KEY',
            'DEEPSEEK_API_KEY',
            'GROQ_API_KEY',
            'CEREBRAS_API_KEY',
            'DASHSCOPE_API_KEY',
            'MOONSHOT_API_KEY',
            'OLLAMA_URL',
            'ICOTES_ROUTE_KEY',
            'ICOTES_ROUTE_URL',
            # Services
            'ELEVENLABS_API_KEY',
            'ATLASCLOUD_API_KEY',
            'MAILERSEND_API_KEY',
            'PUSHOVER_USER',
            'PUSHOVER_TOKEN',
            'TAVILY_API_KEY',
            'SERPER_API_KEY',
        }

        invalid_keys = sorted([k for k in api_keys.keys() if k not in allowed_keys])
        if invalid_keys:
            return {
                "success": False,
                "error": f"Invalid environment setting keys: {', '.join(invalid_keys)}",
            }

        def _sanitize_env_value(value: str) -> str:
            # Prevent writing multi-line values into .env
            if "\n" in value or "\r" in value:
                raise ValueError("Environment values must be single-line")
            return value
        
        # Update environment variables directly in memory
        updated_keys = {}
        for key, value in api_keys.items():
            if value and value.strip():  # Only update non-empty values
                os.environ[key] = _sanitize_env_value(value.strip())
                updated_keys[key] = True
                logger.info(f"Updated environment variable: {key}")
        
        # Persist to .env file for Docker/production persistence
        try:
            # agents.py lives at: backend/icpy/api/endpoints/agents.py
            # parents[3] => backend/, parents[4] => repo root
            from pathlib import Path

            this_file = Path(__file__).resolve()
            backend_dir = str(this_file.parents[3])
            repo_root = str(this_file.parents[4])

            candidate_paths = [
                os.path.join(backend_dir, ".env"),
                os.path.join(repo_root, ".env"),
            ]

            env_file_path = next((p for p in candidate_paths if os.path.exists(p)), os.path.join(repo_root, ".env"))

            existing_lines: list[str] = []
            if os.path.exists(env_file_path):
                with open(env_file_path, 'r', encoding='utf-8') as f:
                    existing_lines = f.readlines()

            # Replace in-place while preserving comments/blank lines.
            # Supports lines like: KEY=..., export KEY=..., with arbitrary whitespace.
            updates = {k: _sanitize_env_value(v.strip()) for k, v in api_keys.items() if v and v.strip()}

            def _quote_env_value(v: str) -> str:
                escaped = v.replace('\\', '\\\\').replace('"', '\\"')
                return f'"{escaped}"'

            key_to_index: dict[str, int] = {}
            export_prefix: dict[str, str] = {}
            pattern = re.compile(r'^\s*(export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=')
            for idx, line in enumerate(existing_lines):
                m = pattern.match(line)
                if not m:
                    continue
                k = m.group(2)
                if k in updates and k not in key_to_index:
                    key_to_index[k] = idx
                    export_prefix[k] = 'export ' if m.group(1) else ''

            new_lines = list(existing_lines)
            for k, v in updates.items():
                new_line = f"{export_prefix.get(k, '')}{k}={_quote_env_value(v)}\n"
                if k in key_to_index:
                    new_lines[key_to_index[k]] = new_line
                else:
                    # Ensure we have a trailing newline before appending a new key
                    if new_lines and not new_lines[-1].endswith('\n'):
                        new_lines[-1] = new_lines[-1] + '\n'
                    new_lines.append(new_line)

            os.makedirs(os.path.dirname(env_file_path) or '.', exist_ok=True)
            with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8', dir=os.path.dirname(env_file_path) or None) as tmp:
                tmp.writelines(new_lines)
                tmp_path = tmp.name
            try:
                os.replace(tmp_path, env_file_path)
            except BaseException:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
                raise

            logger.info(f"Persisted {len(updated_keys)} settings to {env_file_path}")
        except Exception as persist_error:
            logger.warning(f"Failed to persist settings to .env file: {persist_error}")
        
        # Reload environment for agents
        try:
            await reload_agent_environment()
        except Exception as reload_error:
            logger.warning(f"Failed to reload agent environment: {reload_error}")
        
        logger.info(f"Environment settings updated: {list(updated_keys.keys())}")
        
        return {
            "success": True, 
            "updated_keys": list(updated_keys.keys()), 
            "message": f"Updated {len(updated_keys)} environment settings and reloaded environment"
        }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions (like 401)
    except Exception as e:
        logger.error(f"Error updating environment settings: {e}")
        return {"success": False, "error": str(e)}


async def get_api_keys_status_endpoint(request: Request):
    """Get the status of API keys (whether they are set or not, without revealing values)."""
    try:
        # Check authentication in SaaS mode
        if auth_manager and auth_manager.is_saas_mode():
            user = get_optional_user(request)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")

        # Parse explicit keys from query, if provided
        q = request.query_params.get("keys")
        explicit_keys = None
        if q:
            explicit_keys = [k.strip() for k in q.split(',') if k.strip()]

        # Helper to build status map for given keys
        def build_status(keys):
            # Site settings that should not be masked (visible as plain text)
            site_settings = {'SITE_URL', 'WORKSPACE_ROOT', 'PORT'}
            status = {}
            for key in keys:
                value = os.getenv(key)
                if value:
                    # Don't mask site settings - show actual values
                    if key in site_settings:
                        status[key] = {"is_set": True, "masked_value": value, "length": len(value)}
                    else:
                        masked = value[:4] + '*' * (len(value) - 4) if len(value) > 4 else '*' * len(value)
                        status[key] = {"is_set": True, "masked_value": masked, "length": len(value)}
                else:
                    status[key] = {"is_set": False, "masked_value": "", "length": 0}
            return status

        if explicit_keys:
            # Explicit mode: only return requested keys
            return {"success": True, "keys": build_status(explicit_keys)}

        # Auto mode: detect likely API-related keys from environment
        env_keys = list(os.environ.keys())
        candidates = []
        for k in env_keys:
            upper_k = k.upper()
            if (
                upper_k.endswith("API_KEY") or
                upper_k.endswith("_TOKEN") or
                upper_k.endswith("ACCESS_TOKEN") or
                upper_k.endswith("_SECRET") or
                ("API" in upper_k and "KEY" in upper_k)
            ):
                candidates.append(k)
                continue
            # Include common API base URLs like OLLAMA or OPENAI
            if (
                ("OLLAMA" in upper_k or "OPENAI" in upper_k or "ANTHROPIC" in upper_k or "GROQ" in upper_k or "GOOGLE" in upper_k or "MOONSHOT" in upper_k or "DEEPSEEK" in upper_k or "CEREBRAS" in upper_k or "DASHSCOPE" in upper_k)
                and (upper_k.endswith("_URL") or upper_k.endswith("URL") or upper_k.endswith("API_BASE") or upper_k.endswith("_API_BASE") or upper_k.endswith("BASE_URL"))
            ):
                candidates.append(k)

        # De-duplicate while preserving order (case-insensitive for Windows envs)
        seen_ci = set()
        filtered = []
        for k in candidates:
            kk = k.upper()
            if kk in seen_ci:
                continue
            seen_ci.add(kk)
            filtered.append(k)

        return {"success": True, "keys": build_status(filtered)}
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions (like 401)
    except Exception as e:
        logger.error(f"Error getting API key status: {e}")
        return {"success": False, "error": str(e)}


async def get_api_key_value_endpoint(request: Request):
    """Reveal a full environment value for a given key."""
    try:
        # SaaS mode auth check
        if auth_manager and auth_manager.is_saas_mode():
            user = get_optional_user(request)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")

        key = request.query_params.get("key")
        if not key:
            raise HTTPException(status_code=400, detail="Missing 'key' query parameter")

        # Basic key format validation to avoid abusive input
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_\.\-:]{0,127}", key):
            raise HTTPException(status_code=400, detail="Invalid key format")

        # Gate revealing behind:
        #  - Standalone mode (default allow), OR
        #  - Explicit env flag, OR
        #  - Development mode
        standalone_mode = not (ICPY_AVAILABLE and auth_manager and auth_manager.is_saas_mode())
        allow_reveal = (
            standalone_mode
            or os.getenv("NODE_ENV") == "development"
            or os.getenv("ALLOW_KEY_REVEAL", "").lower() in ("1", "true", "yes")
        )
        if not allow_reveal:
            raise HTTPException(status_code=403, detail="Key reveal disabled. Set ALLOW_KEY_REVEAL=true or run in development.")

        # In SaaS mode, optionally require specific roles to reveal keys
        if ICPY_AVAILABLE and auth_manager and auth_manager.is_saas_mode():
            allowed_roles = [r.strip().lower() for r in (os.getenv("KEY_REVEAL_ROLES", "admin,owner")).split(",") if r.strip()]
            role = (user or {}).get("role", "").lower() if user else ""
            if allowed_roles and role not in allowed_roles:
                raise HTTPException(status_code=403, detail="Insufficient role to reveal keys")

        # Enforce allowlist (exact keys) and/or allowed prefixes if provided
        allowlist = [k.strip() for k in os.getenv("KEY_REVEAL_ALLOWLIST", "").split(",") if k.strip()]
        prefixes = [p.strip() for p in os.getenv("KEY_REVEAL_PREFIXES", "").split(",") if p.strip()]
        if allowlist or prefixes:
            if key not in allowlist and not any(key.startswith(p) for p in prefixes):
                raise HTTPException(status_code=403, detail="Key not permitted to reveal")

        value = os.getenv(key)
        if value is None:
            return {"success": False, "error": f"Key '{key}' not found or not set"}

        # Do not log the value; only return it to the caller
        return {"success": True, "key": key, "value": value, "length": len(value)}

    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Error revealing API key value for %s",
            request.query_params.get('key','?')
        )
        return {"success": False, "error": "internal_error"}


async def get_custom_agent_info(agent_name: str):
    """Get information about a specific custom agent."""
    try:
        logger.info(f"Agent info requested for: {agent_name}")
        
        info = get_agent_info(agent_name)
        
        return {"success": True, "agent_info": info}
        
    except ImportError as e:
        logger.warning(f"Agent info system not available: {e}")
        return {"success": False, "error": "Agent info system not available"}
    except Exception as e:
        logger.error(f"Error getting agent info for {agent_name}: {e}")
        return {"success": False, "error": str(e)}