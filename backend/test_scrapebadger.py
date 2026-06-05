import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import requests
import sys
import os
import asyncio
import httpx

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend import (
    fetch_profile_scrapebadger,
    parse_twitter_markdown_profile,
    run_location_intelligence,
)


class TestScrapeBadgerPipeline(unittest.TestCase):

    def test_markdown_parsing_valid(self):
        """Test parsing of a standard valid profile in markdown format."""
        sample_markdown = """
# Deepak | Video Editor
@Viralfy_

⚖️ AI-Powered Video Systems for US Law Firms & Educators
Joined May 2012
125 Following
108 Followers

📍 Location: India
🔗 Website: https://viralfy.co
"""
        parsed = parse_twitter_markdown_profile(sample_markdown, "viralfy_")
        self.assertEqual(parsed["display_name"], "Deepak | Video Editor")
        self.assertEqual(parsed["location"], "India")
        self.assertEqual(parsed["following_count"], 125)
        self.assertEqual(parsed["followers_count"], 108)
        self.assertEqual(parsed["join_date"], "May 2012")
        self.assertEqual(parsed["website"], "https://viralfy.co")
        self.assertIn("AI-Powered Video Systems", parsed["description"])

    def test_markdown_parsing_missing_location(self):
        """Test parsing when profile location is missing."""
        sample_markdown = """
# Anon User
@anon_user

Just a random bio.
100 Following
200 Followers
"""
        parsed = parse_twitter_markdown_profile(sample_markdown, "anon_user")
        self.assertEqual(parsed["location"], "")
        self.assertEqual(parsed["followers_count"], 200)

    def test_markdown_japanese_profile(self):
        """Test parsing of a Japanese user profile."""
        sample_markdown = """
# kasamacura｜AI映像作家
@kasamacura

江戸前寿司の伝統を大切にしながら、現代的な空間美と映像感覚を融合。
1.5K Following
12.3K Followers

📍 Tokyo, Japan
"""
        parsed = parse_twitter_markdown_profile(sample_markdown, "kasamacura")
        self.assertEqual(parsed["location"], "Tokyo, Japan")
        self.assertEqual(parsed["followers_count"], 12300)
        self.assertEqual(parsed["following_count"], 1500)

    def test_markdown_arabic_profile(self):
        """Test parsing of an Arabic user profile."""
        sample_markdown = """
# أحمد الحربي
@alharbi

مطور برمجيات ومهتم بالذكاء الاصطناعي.
500 Following
1M Followers

📍 Riyadh, Saudi Arabia
"""
        parsed = parse_twitter_markdown_profile(sample_markdown, "alharbi")
        self.assertEqual(parsed["location"], "Riyadh, Saudi Arabia")
        self.assertEqual(parsed["followers_count"], 1000000)

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("backend.httpx.AsyncClient.post", new_callable=AsyncMock)
    def test_dns_failure(self, mock_post, mock_sleep):
        """Test handling of DNS lookup failure."""
        # Simulate connection error due to DNS gaierror
        mock_post.side_effect = httpx.ConnectError("Failed to resolve 'scrapebadger.com' (getaddrinfo failed)")
        
        # Temporarily enable key for test
        with patch("backend.SCRAPEBADGER_API_KEY", "test_key"):
            res = asyncio.run(fetch_profile_scrapebadger("testuser"))
            self.assertEqual(res["status"], "error")
            self.assertEqual(res["reason"], "dns_resolution_failed")

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("backend.httpx.AsyncClient.post", new_callable=AsyncMock)
    def test_timeout(self, mock_post, mock_sleep):
        """Test handling of request timeouts."""
        mock_post.side_effect = httpx.TimeoutException("Request timed out")
        
        with patch("backend.SCRAPEBADGER_API_KEY", "test_key"):
            res = asyncio.run(fetch_profile_scrapebadger("testuser"))
            self.assertEqual(res["status"], "error")
            self.assertEqual(res["reason"], "timeout")

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("backend.httpx.AsyncClient.post", new_callable=AsyncMock)
    def test_private_or_suspended_account(self, mock_post, mock_sleep):
        """Test handling of client error responses (like 404 for suspended/private accounts)."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response
        
        with patch("backend.SCRAPEBADGER_API_KEY", "test_key"):
            res = asyncio.run(fetch_profile_scrapebadger("testuser"))
            self.assertEqual(res["status"], "error")
            self.assertEqual(res["reason"], "http_404_client_error")


if __name__ == "__main__":
    unittest.main()
