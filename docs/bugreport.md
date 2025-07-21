# Bug Report: Incorrect Handling of Optional Parameters in Terminal Creation

**Date:** 2025-07-21
**Author:** Jules

## Description

A bug has been identified in the `create_terminal` endpoint of the REST API (`backend/icpy/api/rest_api.py`). The current implementation incorrectly handles optional parameters (`shell`, `cwd`, `env`, `rows`, `cols`, and `name`) when creating a new terminal session.

The code uses `hasattr` and a truthiness check (`and request.shell`) to determine whether to set a value on the `TerminalConfig` object. This logic fails to distinguish between a parameter that is not provided and a parameter that is provided with a `None` or empty value. This can lead to unexpected behavior, as `None` values are not propagated to the `terminal_service`, and the default values in `TerminalConfig` are used instead.

## Location

- **File:** `backend/icpy/api/rest_api.py`
- **Function:** `create_terminal` within `_register_terminal_routes`

## Problematic Code

```python
                # Create terminal configuration
                config = TerminalConfig()
                if hasattr(request, 'shell') and request.shell:
                    config.shell = request.shell
                if hasattr(request, 'cwd') and request.cwd:
                    config.cwd = request.cwd
                if hasattr(request, 'env') and request.env:
                    config.env = request.env
                if hasattr(request, 'rows') and request.rows:
                    config.rows = request.rows
                if hasattr(request, 'cols') and request.cols:
                    config.cols = request.cols

                terminal_id = await self.terminal_service.create_session(
                    name=getattr(request, 'name', None),
                    config=config
                )
```

## Impact

This bug prevents users from explicitly setting `None` or empty values for optional terminal parameters. For example, a user cannot create a terminal with an empty environment by passing `env={}`. Instead, the default environment from `TerminalConfig` will be used.

## Recommended Fix

The code should be refactored to check if the parameters are not `None` before setting them, rather than checking for truthiness. This will ensure that explicitly provided `None` values are respected.

```python
                # Create terminal configuration
                config = TerminalConfig()
                if request.shell is not None:
                    config.shell = request.shell
                if request.cwd is not None:
                    config.cwd = request.cwd
                if request.env is not None:
                    config.env = request.env
                if request.rows is not None:
                    config.rows = request.rows
                if request.cols is not None:
                    config.cols = request.cols

                terminal_id = await self.terminal_service.create_session(
                    name=request.name,
                    config=config
                )
```
