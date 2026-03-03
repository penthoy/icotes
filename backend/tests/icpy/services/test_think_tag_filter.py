"""Tests for ThinkTagFilter in chat_service."""

import pytest
from icpy.services.chat_service import ThinkTagFilter


class TestThinkTagFilter:
    """Test streaming <think> tag stripping."""

    def test_no_think_tags(self):
        f = ThinkTagFilter()
        assert f.feed("Hello world") == "Hello world"
        assert f.flush() == ""

    def test_complete_think_block_single_chunk(self):
        f = ThinkTagFilter()
        result = f.feed("<think>internal reasoning</think>Hello!")
        assert result == "Hello!"

    def test_think_block_at_end(self):
        f = ThinkTagFilter()
        result = f.feed("Hello!<think>internal reasoning</think>")
        assert result == "Hello!"

    def test_think_block_in_middle(self):
        f = ThinkTagFilter()
        result = f.feed("Hi <think>reasoning</think> there!")
        assert result == "Hi  there!"

    def test_think_block_spans_two_chunks(self):
        f = ThinkTagFilter()
        r1 = f.feed("Hello <think>start of")
        r2 = f.feed(" reasoning</think> world")
        assert r1 == "Hello "
        assert r2 == " world"

    def test_think_tag_split_across_chunks(self):
        """Opening tag arrives in pieces across chunks."""
        f = ThinkTagFilter()
        r1 = f.feed("Hello <thi")
        r2 = f.feed("nk>hidden</think> visible")
        assert r1 + r2 == "Hello  visible"

    def test_closing_tag_split_across_chunks(self):
        """Closing tag arrives in pieces across chunks."""
        f = ThinkTagFilter()
        r1 = f.feed("<think>hidden</thi")
        r2 = f.feed("nk>visible")
        assert r1 + r2 == "visible"

    def test_multiple_think_blocks(self):
        f = ThinkTagFilter()
        result = f.feed("<think>first</think>A<think>second</think>B")
        assert result == "AB"

    def test_unclosed_think_block_discards_rest(self):
        f = ThinkTagFilter()
        r1 = f.feed("<think>this never closes")
        r2 = f.feed(" still thinking")
        r3 = f.flush()
        assert r1 + r2 + r3 == ""

    def test_flush_emits_buffered_non_think_text(self):
        """Partial tag prefix that turns out to not be a tag."""
        f = ThinkTagFilter()
        r1 = f.feed("Hello <thi")
        # No more input — flush releases the buffer
        r2 = f.flush()
        assert r1 + r2 == "Hello <thi"

    def test_empty_think_block(self):
        f = ThinkTagFilter()
        result = f.feed("<think></think>Hi")
        assert result == "Hi"

    def test_only_think_block(self):
        f = ThinkTagFilter()
        result = f.feed("<think>The user just said Hey</think>")
        remaining = f.flush()
        assert result + remaining == ""

    def test_real_world_minimax_output(self):
        """Simulates the actual MiniMax M2.5 output from the bug report."""
        f = ThinkTagFilter()
        chunks = [
            '<think>\nThe user just said "Hey"',
            ' twice. This is a simple greeting,',
            " so I should respond in a friendly",
            ", conversational way without using any tools.\n</think>",
            "\nHey there! 👋 How can I help you today?",
        ]
        result = ""
        for c in chunks:
            result += f.feed(c)
        result += f.flush()
        assert result == "\nHey there! 👋 How can I help you today?"
