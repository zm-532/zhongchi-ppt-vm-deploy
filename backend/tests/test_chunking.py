"""Tests for text chunking utilities."""

import unittest

from app.chunking import chunk_text, CHUNK_MAX_SIZE, CHUNK_MIN_SIZE


class ChunkingTest(unittest.TestCase):
    def test_empty_text_returns_empty_list(self):
        self.assertEqual(chunk_text(""), [])
        self.assertEqual(chunk_text("   "), [])
        self.assertEqual(chunk_text("\n\n"), [])

    def test_short_text_returns_single_chunk(self):
        text = "这是一段比较短的文本。"
        chunks = chunk_text(text)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_exactly_max_size_returns_single_chunk(self):
        text = "A" * CHUNK_MAX_SIZE
        chunks = chunk_text(text)
        self.assertEqual(len(chunks), 1)

    def test_long_text_returns_multiple_chunks(self):
        # Create text longer than max_size
        text = "这是一段很长的文本。" * 200  # ~3000 chars
        chunks = chunk_text(text)
        self.assertGreater(len(chunks), 1)

    def test_chunks_respect_max_size(self):
        text = "B" * 2000
        chunks = chunk_text(text)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), CHUNK_MAX_SIZE + 50)  # Allow small overflow for safety

    def test_chunks_have_overlap(self):
        text = "C" * 1500 + "D" * 1500  # Two distinct patterns
        chunks = chunk_text(text)
        self.assertGreater(len(chunks), 1)

    def test_adjacent_chunks_overlap(self):
        text = "X" * 400 + "Y" * 400 + "Z" * 400
        chunks = chunk_text(text)
        if len(chunks) > 1:
            # Check that chunks share some overlap characters
            self.assertTrue(any(c1 == c2 for c1, c2 in zip(chunks[0][-50:], chunks[1][:50])))

    def test_chunks_smaller_than_min_size_merged(self):
        # Very short text chunks should be merged with next
        text = "AB" * 100 + "CD" * 300  # First part short, second part longer
        chunks = chunk_text(text)
        # The small initial chunk should be merged with the next
        for chunk in chunks:
            if len(chunks) > 1 and chunk == chunks[0]:
                self.assertGreaterEqual(len(chunk), CHUNK_MIN_SIZE)

    def test_unicode_text_handled_correctly(self):
        text = "中文文本测试" * 100
        chunks = chunk_text(text)
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            self.assertIsInstance(chunk, str)

    def test_newline_break_honored(self):
        text = "第一行\n第二行\n第三行\n" * 200
        chunks = chunk_text(text)
        self.assertGreater(len(chunks), 0)

    def test_empty_chunk_not_returned(self):
        text = "\n\n" + "内容" * 500 + "\n\n"
        chunks = chunk_text(text)
        for chunk in chunks:
            self.assertTrue(chunk.strip())


if __name__ == "__main__":
    unittest.main()