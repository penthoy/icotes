"""
Tests for WhatsApp Message Formatter.

Tests the text cleaning, tool marker stripping, and media path extraction
from AI agent output.
"""

import json
import pytest

from icpy.services.whatsapp.whatsapp_bot_service import WhatsAppMessageFormatter


class TestCleanForWhatsApp:
    """Tests for cleaning AI output for WhatsApp display."""

    def test_plain_text_unchanged(self):
        text = "Hello, how can I help you today?"
        assert WhatsAppMessageFormatter.clean_for_whatsapp(text) == text

    def test_strips_tool_start_markers(self):
        text = "📋 **generate_image**: {\"prompt\": \"a cat\"}\nHere is your image!"
        cleaned = WhatsAppMessageFormatter.clean_for_whatsapp(text)
        assert "📋" not in cleaned
        assert "generate_image" not in cleaned
        assert "Here is your image!" in cleaned

    def test_strips_tool_success_markers(self):
        text = '✅ **Success**: {"absolutePath": "/tmp/test.png"}\nDone!'
        cleaned = WhatsAppMessageFormatter.clean_for_whatsapp(text)
        assert "✅" not in cleaned
        assert "absolutePath" not in cleaned
        assert "Done!" in cleaned

    def test_strips_tool_error_markers(self):
        text = "❌ **Error**: Something went wrong\nSorry about that."
        cleaned = WhatsAppMessageFormatter.clean_for_whatsapp(text)
        assert "❌" not in cleaned
        assert "Something went wrong" not in cleaned
        assert "Sorry about that." in cleaned

    def test_strips_status_markers(self):
        text = "🔧 **Executing tools...**\nProcessing your request.\n🔧 **Tool execution complete. Continuing...**\nDone."
        cleaned = WhatsAppMessageFormatter.clean_for_whatsapp(text)
        assert "🔧" not in cleaned
        assert "Executing tools" not in cleaned
        assert "Done." in cleaned

    def test_strips_markdown_image_links(self):
        text = "Here is the result:\n![Generated image](file:///tmp/image.png)\nEnjoy!"
        cleaned = WhatsAppMessageFormatter.clean_for_whatsapp(text)
        assert "![" not in cleaned
        assert "file:///" not in cleaned
        assert "Enjoy!" in cleaned

    def test_collapses_excessive_newlines(self):
        text = "Line 1\n\n\n\n\nLine 2"
        cleaned = WhatsAppMessageFormatter.clean_for_whatsapp(text)
        assert "\n\n\n" not in cleaned
        assert "Line 1" in cleaned
        assert "Line 2" in cleaned


class TestExtractMediaPaths:
    """Tests for extracting media file paths from tool call output."""

    def test_extract_image_path(self):
        text = (
            '📋 **generate_image**: {"prompt": "a cute cat"}\n'
            '✅ **Success**: {"absolutePath": "/tmp/images/cat.png", "model": "dall-e-3"}\n'
        )
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        assert len(media) == 1
        assert media[0]["type"] == "image"
        assert media[0]["path"] == "/tmp/images/cat.png"

    def test_extract_image_with_image_reference(self):
        text = (
            '📋 **generate_image**: {"prompt": "sunset"}\n'
            '✅ **Success**: {"imageReference": {"absolute_path": "/tmp/sunset.jpg"}, "model": "dall-e-3"}\n'
        )
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        assert len(media) == 1
        assert media[0]["path"] == "/tmp/sunset.jpg"

    def test_extract_video_path(self):
        text = (
            '📋 **image_to_video**: {"prompt": "animate the cat"}\n'
            '✅ **Success**: {"absolute_path": "/tmp/videos/cat.mp4", "model": "minimax"}\n'
        )
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        assert len(media) == 1
        assert media[0]["type"] == "video"
        assert media[0]["path"] == "/tmp/videos/cat.mp4"

    def test_strips_file_protocol(self):
        text = (
            '📋 **generate_image**: {"prompt": "test"}\n'
            '✅ **Success**: {"absolutePath": "file:///tmp/test.png"}\n'
        )
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        assert len(media) == 1
        assert media[0]["path"] == "/tmp/test.png"

    def test_no_media_in_plain_text(self):
        text = "Just some regular text with no tool calls."
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        assert len(media) == 0

    def test_non_media_tool_ignored(self):
        text = (
            '📋 **web_search**: {"query": "weather"}\n'
            '✅ **Success**: {"results": "sunny"}\n'
        )
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        assert len(media) == 0

    def test_multiple_media(self):
        text = (
            '📋 **generate_image**: {"prompt": "cat"}\n'
            '✅ **Success**: {"absolutePath": "/tmp/cat.png"}\n'
            '📋 **generate_image**: {"prompt": "dog"}\n'
            '✅ **Success**: {"absolutePath": "/tmp/dog.png"}\n'
        )
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        assert len(media) == 2
        assert media[0]["path"] == "/tmp/cat.png"
        assert media[1]["path"] == "/tmp/dog.png"

    def test_extract_tts_audio_file_key(self):
        """Route-proxy TTS tool returns audio_file key."""
        text = (
            '📋 **text_to_speech**: {"text": "Good morning!", "voice": "tao2"}\n'
            '✅ **Success**: {"audio_file": "/workspace/good_morning_tao2.mp3", "voice": "tao2", "duration_seconds": 1.4}\n'
        )
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        assert len(media) == 1
        assert media[0]["type"] == "audio"
        assert media[0]["path"] == "/workspace/good_morning_tao2.mp3"

    def test_extract_tts_absolute_path_key(self):
        """Local ElevenLabs TTS tool returns absolute_path key."""
        text = (
            '📋 **text_to_speech**: {"text": "Hello!", "voice": "george"}\n'
            '✅ **Success**: {"absolute_path": "/workspace/sounds/hello.mp3", "saved": true}\n'
        )
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        assert len(media) == 1
        assert media[0]["type"] == "audio"
        assert media[0]["path"] == "/workspace/sounds/hello.mp3"

    def test_extract_tts_prompt_from_text_field(self):
        """TTS audio item uses the text content as prompt."""
        text = (
            '📋 **text_to_speech**: {"text": "Good morning!", "voice": "tao2"}\n'
            '✅ **Success**: {"audio_file": "/workspace/gm.mp3", "text": "Good morning!"}\n'
        )
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        assert len(media) == 1
        assert media[0]["prompt"] == "Good morning!"

    def test_extract_tts_python_dict_payload(self):
        """WhatsApp stream may contain Python repr payload with single quotes."""
        text = (
            "📋 **text_to_speech**: {'text': 'Good morning!', 'voice': 'tao2'}\n"
            "✅ **Success**: {'saved': True, 'file_path': 'sounds/tts_Good_morning_1772207746.mp3', 'text': 'Good morning!'}\n"
        )
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        assert len(media) == 1
        assert media[0]["type"] == "audio"
        assert media[0]["path"] == "sounds/tts_Good_morning_1772207746.mp3"

    def test_extract_tts_fallback_path_from_truncated_payload(self):
        """Truncated paths (containing '...') should be rejected so text-fallback can find the real path."""
        text = (
            "📋 **text_to_speech**: {'text': 'Good morning!', 'voice': 'tao2'}\n"
            "✅ **Success**: {'saved': True, 'file_path': 'sounds/tts_Good_morning_17722077... (truncated)\n"
        )
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        # No readable text fallback provided, so nothing should be extracted
        assert len(media) == 0

    def test_extract_text_to_video_path(self):
        text = (
            '📋 **text_to_video**: {"prompt": "horse on mountain", "duration": 8}\n'
            '✅ **Success**: {"file_path": "videos/horse_mountain_galloping.mp4", "absolute_path": "/workspace/videos/horse_mountain_galloping.mp4"}\n'
        )
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        assert len(media) == 1
        assert media[0]["type"] == "video"
        assert media[0]["path"] == "/workspace/videos/horse_mountain_galloping.mp4"

    def test_extract_text_to_video_python_dict_payload(self):
        text = (
            "📋 **text_to_video**: {'prompt': 'horse on mountain'}\n"
            "✅ **Success**: {'saved': True, 'file_path': 'videos/horse_mountain_galloping.mp4'}\n"
        )
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        assert len(media) == 1
        assert media[0]["type"] == "video"
        assert media[0]["path"] == "videos/horse_mountain_galloping.mp4"

    def test_extract_text_to_video_fallback_from_truncated_payload(self):
        text = (
            "📋 **text_to_video**: {'prompt': 'horse on mountain'}\n"
            "✅ **Success**: {'saved': True, 'file_path': 'videos/horse_mountain_galloping.mp4\n"
        )
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        assert len(media) == 1
        assert media[0]["type"] == "video"
        assert media[0]["path"] == "videos/horse_mountain_galloping.mp4"

    def test_text_fallback_extracts_tts_from_saved_to_line(self):
        """When tool payload is fully truncated, extract path from AI's readable text."""
        text = (
            "📋 **text_to_speech**: {'text': 'Magandang umaga', 'voice': 'tao2', 'model_id': 'eleven_multilingual_v2'}\n"
            "✅ **Success**: {'text_length': 15, 'voice_id': 'tao2', 'model_id': 'eleven_multilingual_v2', "
            "'output_format': 'mp3_44100_128', 'audio_size_bytes': 18016, 'saved': True, "
            "'file_path': 'sounds/tts_Magandang_umaga_17722... (truncated)\n"
            "\n🔧 **Tool execution complete. Continuing...**\n\n"
            "Done! 🌅\n\n"
            "Here's \"Magandang umaga\" (Good morning in Tagalog) with the tao2 voice:\n\n"
            "📁 Saved to: `local:/home/penthoy/icotes/workspace/sounds/tts_Magandang_umaga_1772209701.mp3`"
        )
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        assert len(media) >= 1
        audio_items = [m for m in media if m["type"] == "audio"]
        assert len(audio_items) == 1
        assert audio_items[0]["path"] == "/home/penthoy/icotes/workspace/sounds/tts_Magandang_umaga_1772209701.mp3"

    def test_text_fallback_extracts_video_from_saved_to_line(self):
        """When video tool payload is truncated, extract path from AI's readable text."""
        text = (
            "📋 **text_to_video**: {'prompt': 'monk meditating'}\n"
            "✅ **Success**: {'file_path': 'videos/ttv_A_serene_Buddhist_monk_seedance-... (truncated)\n"
            "\n🔧 **Tool execution complete. Continuing...**\n\n"
            "Done! 🧘\n\n"
            "📁 Saved to: `local:/home/penthoy/icotes/workspace/videos/ttv_monk_1772209299.mp4`"
        )
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        assert len(media) >= 1
        video_items = [m for m in media if m["type"] == "video"]
        assert len(video_items) == 1
        assert video_items[0]["path"] == "/home/penthoy/icotes/workspace/videos/ttv_monk_1772209299.mp4"

    def test_text_fallback_skips_when_tool_extraction_already_succeeded(self):
        """When tool payload extraction succeeded, text fallback should not duplicate."""
        text = (
            '📋 **text_to_speech**: {"text": "Hello!", "voice": "george"}\n'
            '✅ **Success**: {"absolute_path": "/workspace/sounds/hello.mp3", "saved": true}\n'
            "\n🔧 **Tool execution complete. Continuing...**\n\n"
            "Done! Saved to: `local:/workspace/sounds/hello.mp3`"
        )
        media = WhatsAppMessageFormatter.extract_media_paths(text)
        assert len(media) == 1  # No duplicate
