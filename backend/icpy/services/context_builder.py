"""
Context Builder for Agent Message History

Provides smart context building that avoids loading full images into agent context
unless explicitly needed. Part of Phase 2: Context Building.

Key Features:
- Loads ImageReference metadata instead of full base64
- Selective image loading based on recency and relevance
- Thumbnail-based visual context
- Configurable context strategies
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from ..services.image_cache import get_image_cache
from ..services.image_resolver import ImageResolver

logger = logging.getLogger(__name__)


class ContextStrategy(Enum):
    """Strategy for including images in context"""
    METADATA_ONLY = "metadata_only"  # Only ImageReference metadata, no base64
    THUMBNAILS_ONLY = "thumbnails_only"  # Small thumbnails for visual context
    RECENT_FULL = "recent_full"  # Full images for N most recent only
    SELECTIVE = "selective"  # Load full images based on relevance hints
    ALL_FULL = "all_full"  # Load all images (legacy behavior, not recommended)


@dataclass
class ContextConfig:
    """Configuration for context building"""
    strategy: ContextStrategy = ContextStrategy.METADATA_ONLY
    max_full_images: int = 3  # For RECENT_FULL strategy
    include_thumbnails: bool = True  # Include thumbnails in metadata
    max_history_length: int = 10  # Number of messages to include
    workspace_path: Optional[str] = None  # For image resolution


class ContextBuilder:
    """
    Builds optimized context for AI agents from message history.
    
    Prevents token exhaustion by not loading full base64 images unless needed.
    """
    
    def __init__(self, workspace_path: Optional[str] = None):
        """
        Initialize context builder.
        
        Args:
            workspace_path: Path to workspace for image resolution
        """
        self.workspace_path = workspace_path
        self.image_cache = get_image_cache()
        self.image_resolver = ImageResolver(workspace_path) if workspace_path else None
    
    def build_context(
        self,
        messages: List[Any],  # List of ChatMessage objects
        config: Optional[ContextConfig] = None
    ) -> List[Dict[str, Any]]:
        """
        Build optimized context from message history.
        
        Args:
            messages: List of ChatMessage objects from history
            config: Configuration for context building
        
        Returns:
            List of message dicts suitable for AI context
        """
        if config is None:
            config = ContextConfig()
        
        context = []
        recent_images_count = 0
        
        for msg in messages:
            # Convert message to dict
            msg_dict = msg.to_dict() if hasattr(msg, 'to_dict') else msg
            
            # Process message based on strategy
            processed_msg = self._process_message(
                msg_dict,
                config,
                recent_images_count
            )
            
            # Track recent images for RECENT_FULL strategy
            if self._has_image_reference(msg_dict):
                recent_images_count += 1
            
            context.append(processed_msg)
        
        return context
    
    def _process_message(
        self,
        msg_dict: Dict[str, Any],
        config: ContextConfig,
        recent_images_count: int
    ) -> Dict[str, Any]:
        """
        Process a single message according to context strategy.
        
        Args:
            msg_dict: Message dictionary
            config: Context configuration
            recent_images_count: Number of recent images seen so far
        
        Returns:
            Processed message dictionary
        """
        # Check if message contains ImageReference
        if not self._has_image_reference(msg_dict):
            return msg_dict
        
        # Apply strategy
        if config.strategy == ContextStrategy.METADATA_ONLY:
            return self._process_metadata_only(msg_dict, config)
        
        elif config.strategy == ContextStrategy.THUMBNAILS_ONLY:
            return self._process_thumbnails_only(msg_dict, config)
        
        elif config.strategy == ContextStrategy.RECENT_FULL:
            # Load full image only for the N most recent
            if recent_images_count < config.max_full_images:
                return self._process_with_full_image(msg_dict, config)
            else:
                return self._process_metadata_only(msg_dict, config)
        
        elif config.strategy == ContextStrategy.SELECTIVE:
            # Check for relevance hints in metadata
            if self._is_image_relevant(msg_dict):
                return self._process_with_full_image(msg_dict, config)
            else:
                return self._process_metadata_only(msg_dict, config)
        
        elif config.strategy == ContextStrategy.ALL_FULL:
            return self._process_with_full_image(msg_dict, config)
        
        return msg_dict
    
    def _has_image_reference(self, msg_dict: Dict[str, Any]) -> bool:
        """Check if message contains an ImageReference"""
        metadata = msg_dict.get('metadata', {})
        
        # Check common locations for imageReference
        if 'tool_output' in metadata:
            tool_output = metadata['tool_output']
            if isinstance(tool_output, dict) and 'imageReference' in tool_output:
                return True
        
        if 'response' in metadata:
            response = metadata['response']
            if isinstance(response, dict) and 'imageReference' in response:
                return True
        
        return False
    
    def _process_metadata_only(
        self,
        msg_dict: Dict[str, Any],
        config: ContextConfig
    ) -> Dict[str, Any]:
        """
        Process message with metadata only (no base64).
        
        Keeps ImageReference with thumbnail if configured.
        Removes any existing imageData.
        """
        # Deep copy to avoid modifying original
        import copy
        processed = copy.deepcopy(msg_dict)
        metadata = processed.get('metadata', {})
        
        # Process tool_output
        if 'tool_output' in metadata:
            tool_output = metadata['tool_output']
            if isinstance(tool_output, dict):
                # Remove imageData if present
                if 'imageData' in tool_output:
                    del tool_output['imageData']
                
                # Process imageReference if present
                if 'imageReference' in tool_output:
                    ref = tool_output['imageReference']
                    
                    # Create lightweight reference
                    lightweight_ref = {
                        'image_id': ref.get('image_id'),
                        'filename': ref.get('current_filename') or ref.get('original_filename'),
                        'relative_path': ref.get('relative_path'),
                        'prompt': ref.get('prompt'),
                        'model': ref.get('model'),
                        'size_bytes': ref.get('size_bytes'),
                        'mime_type': ref.get('mime_type')
                    }
                    
                    # Include thumbnail if configured
                    if config.include_thumbnails:
                        lightweight_ref['thumbnail_base64'] = ref.get('thumbnail_base64')
                        lightweight_ref['thumbnail_size'] = len(ref.get('thumbnail_base64', ''))
                    
                    tool_output['imageReference'] = lightweight_ref
        
        # Also check response location
        if 'response' in metadata:
            response = metadata['response']
            if isinstance(response, dict):
                if 'imageData' in response:
                    del response['imageData']
        
        return processed
    
    def _process_thumbnails_only(
        self,
        msg_dict: Dict[str, Any],
        config: ContextConfig
    ) -> Dict[str, Any]:
        """
        Process message with thumbnails for visual context.
        
        Similar to metadata_only but always includes thumbnails.
        """
        config_with_thumbnails = ContextConfig(
            strategy=config.strategy,
            include_thumbnails=True,
            max_full_images=config.max_full_images,
            max_history_length=config.max_history_length,
            workspace_path=config.workspace_path
        )
        return self._process_metadata_only(msg_dict, config_with_thumbnails)
    
    def _process_with_full_image(
        self,
        msg_dict: Dict[str, Any],
        config: ContextConfig
    ) -> Dict[str, Any]:
        """
        Process message with full image loaded from cache or disk.
        
        Attempts to load full base64 from:
        1. Memory cache (if recently accessed)
        2. Disk file (via image resolver)
        
        Falls back to metadata-only if loading fails.
        """
        processed = msg_dict.copy()
        metadata = processed.get('metadata', {})
        
        # Find imageReference
        image_ref = None
        location = None
        
        if 'tool_output' in metadata:
            tool_output = metadata['tool_output']
            if isinstance(tool_output, dict) and 'imageReference' in tool_output:
                image_ref = tool_output['imageReference']
                location = 'tool_output'
        
        if not image_ref:
            return self._process_metadata_only(msg_dict, config)
        
        # Try to load full image
        image_id = image_ref.get('image_id')
        
        # Check cache first
        cached_base64 = self.image_cache.get(image_id) if image_id else None
        
        if cached_base64:
            logger.debug(f"Loaded full image from cache: {image_id}")
            metadata[location]['imageData'] = cached_base64
            return processed
        
        # Try to load from disk
        if self.image_resolver and image_id:
            try:
                # Resolve image path (sync operation)
                import asyncio
                try:
                    # Try to get running loop
                    loop = asyncio.get_running_loop()
                    # We're in an async context, but resolve_image_path is async
                    # For now, skip async resolution in sync context
                    # TODO: Make build_context async in future
                    logger.debug(f"Skipping async resolution in sync context for {image_id}")
                    resolved_path = None
                except RuntimeError:
                    # No running loop, can't use async
                    resolved_path = None
                
                # Fallback: try direct path from reference
                if not resolved_path:
                    abs_path = image_ref.get('absolute_path')
                    if abs_path:
                        from pathlib import Path
                        resolved_path = Path(abs_path)
                
                if resolved_path and resolved_path.exists():
                    # Read and encode image
                    import base64
                    with open(resolved_path, 'rb') as f:
                        image_bytes = f.read()
                    
                    full_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    
                    # Cache it for next time
                    mime_type = image_ref.get('mime_type', 'image/png')
                    self.image_cache.put(image_id, full_base64, mime_type)
                    
                    logger.debug(f"Loaded full image from disk: {resolved_path}")
                    metadata[location]['imageData'] = full_base64
                    return processed
                    
            except Exception as e:
                logger.warning(f"Failed to load full image {image_id}: {e}")
        
        # Fallback to metadata only
        logger.info(f"Could not load full image {image_id}, using metadata only")
        return self._process_metadata_only(msg_dict, config)
    
    def _is_image_relevant(self, msg_dict: Dict[str, Any]) -> bool:
        """
        Check if image is relevant for SELECTIVE strategy.
        
        Looks for hints in metadata like:
        - Recent mention of "image", "edit", "modify"
        - Agent explicitly requesting image context
        - User asking about the image
        """
        content = msg_dict.get('content', '').lower()
        
        # Keywords that suggest image relevance
        image_keywords = [
            'image', 'picture', 'photo', 'edit', 'modify',
            'change', 'update', 'fix', 'adjust', 'red hat',
            'color', 'resize', 'crop', 'filter'
        ]
        
        for keyword in image_keywords:
            if keyword in content:
                return True
        
        return False


def create_context_builder(workspace_path: Optional[str] = None) -> ContextBuilder:
    """
    Factory function to create a ContextBuilder instance.
    
    Args:
        workspace_path: Path to workspace for image resolution
    
    Returns:
        ContextBuilder instance
    """
    return ContextBuilder(workspace_path)
