"""
Web search tool powered by Tavily API

Usage: requires TAVILY_API_KEY set in the backend environment.
Lightweight HTTP via requests; no extra SDK dependency.
"""
from __future__ import annotations

import os
import logging
from typing import Any, Dict, Optional

import requests

from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
	"""Perform web searches using the Tavily API."""

	def __init__(self):
		super().__init__()
		self.name = "web_search"
		self.description = "Search the web for up-to-date information using Tavily"
		self.parameters = {
			"type": "object",
			"properties": {
				"query": {
					"type": "string",
					"description": "Search query"
				},
				"maxResults": {
					"type": "integer",
					"description": "Maximum number of results to return (1-10, default 5)"
				},
				"searchDepth": {
					"type": "string",
					"enum": ["basic", "advanced"],
					"description": "Search depth (basic or advanced)"
				},
				"includeAnswer": {
					"type": "boolean",
					"description": "Include a summarized answer when available"
				}
			},
			"required": ["query"]
		}
		self._endpoint = "https://api.tavily.com/search"

	def _get_api_key(self) -> Optional[str]:
		return os.environ.get("TAVILY_API_KEY")

	def _build_payload(self, query: str, max_results: Optional[int], depth: Optional[str], include_answer: bool) -> Dict[str, Any]:
		payload: Dict[str, Any] = {
			"api_key": self._get_api_key(),
			"query": query,
			"search_depth": depth or "basic",
			"max_results": max(1, min(int(max_results or 5), 10)),
			"include_answer": bool(include_answer),
		}
		return payload

	async def execute(self, **kwargs) -> ToolResult:
		try:
			query = kwargs.get("query")
			if not query or not str(query).strip():
				return ToolResult(success=False, error="query is required and cannot be empty")

			api_key = self._get_api_key()
			if not api_key:
				return ToolResult(success=False, error="TAVILY_API_KEY is not set in the environment")

			max_results = kwargs.get("maxResults")
			depth = kwargs.get("searchDepth")
			include_answer = bool(kwargs.get("includeAnswer", True))

			payload = self._build_payload(str(query), max_results, depth, include_answer)

			# Perform the request
			try:
				resp = requests.post(self._endpoint, json=payload, timeout=20)
			except Exception as e:
				logger.error(f"WebSearch request failed: {e}")
				return ToolResult(success=False, error=f"Request failed: {str(e)}")

			if resp.status_code != 200:
				# Try to extract error message
				try:
					data = resp.json()
					err = data.get("error") or data
				except Exception:
					err = resp.text
				return ToolResult(success=False, error=f"Tavily API error {resp.status_code}: {err}")

			try:
				data = resp.json()
			except ValueError:
				return ToolResult(success=False, error="Invalid JSON response from Tavily")

			# Normalize output: include answer (if any) and top results (url, title, content)
			answer = data.get("answer") or data.get("summary")
			results = data.get("results") or []
			normalized = {
				"answer": answer,
				"results": [
					{
						"url": r.get("url"),
						"title": r.get("title"),
						"content": r.get("content") or r.get("snippet")
					}
					for r in results
				]
			}

			return ToolResult(success=True, data=normalized)

		except Exception as e:
			logger.error(f"WebSearchTool error: {e}")
			return ToolResult(success=False, error=str(e))
