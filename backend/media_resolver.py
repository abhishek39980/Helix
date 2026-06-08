import os
import re
import shutil
import httpx
import logging
import subprocess
import json
from typing import Optional, Tuple
from urllib.parse import urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger("helix.media_resolver")

class MediaResolver:
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.timeout = 30.0

    def has_binary(self, name: str) -> bool:
        return shutil.which(name) is not None

    def validate_magic_bytes(self, content: bytes) -> bool:
        if len(content) < 4:
            return False
        # PNG
        if content.startswith(b'\x89PNG\r\n\x1a\n'):
            return True
        # JPEG
        if content.startswith(b'\xff\xd8\xff'):
            return True
        # GIF
        if content.startswith(b'GIF8'):
            return True
        # WebM / MKV (EBML)
        if content.startswith(b'\x1a\x45\xdf\xa3'):
            return True
        # MP4 (offset 4 has ftyp)
        if len(content) >= 8 and content[4:8] == b'ftyp':
            return True
        # AVI (RIFF + AVI)
        if content.startswith(b'RIFF') and len(content) >= 12 and content[8:12] == b'AVI ':
            return True
        return False

    def validate_mime_and_size(self, content: bytes, content_type: str) -> Tuple[bool, str]:
        if len(content) > 250 * 1024 * 1024:
            return False, "file_too_large"
        
        # General checks (HTML rejection)
        content_type_lower = content_type.lower()
        if "text/html" in content_type_lower or content.strip().lower().startswith(b"<html") or content.strip().lower().startswith(b"<!doctype"):
            return False, "rejected_html_content"
            
        # In strict mode, check magic bytes directly
        if self.strict_mode:
            if not self.validate_magic_bytes(content):
                return False, "invalid_magic_bytes"
        
        return True, "ok"

    async def resolve_direct_url(self, url: str) -> Optional[Tuple[bytes, str]]:
        """Downloads direct URL and validates content."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    content = resp.content
                    content_type = resp.headers.get("Content-Type", "application/octet-stream")
                    valid, reason = self.validate_mime_and_size(content, content_type)
                    if valid:
                        return content, content_type
                    else:
                        logger.warning(f"Validation failed for {url}: {reason}")
        except Exception as e:
            logger.error(f"Failed direct URL fetch for {url}: {e}")
        return None

    async def resolve_fxtwitter(self, url: str) -> Optional[Tuple[bytes, str]]:
        """Rewrites x.com/twitter.com to fxtwitter.com to extract video link."""
        parsed = urlparse(url)
        fx_netloc = parsed.netloc.replace("twitter.com", "fxtwitter.com").replace("x.com", "fxtwitter.com")
        fx_url = parsed._replace(netloc=fx_netloc).geturl()
        
        logger.info(f"FxTwitter redirect request: {fx_url}")
        headers = {"User-Agent": "Mozilla/5.0 (compatible; HelixBot/1.0)"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(fx_url, headers=headers)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    video_meta = soup.find("meta", property="og:video") or soup.find("meta", property="og:video:secure_url") or soup.find("meta", property="twitter:player:stream")
                    if video_meta and video_meta.get("content"):
                        video_url = video_meta["content"]
                        logger.info(f"FxTwitter extracted video URL: {video_url}")
                        return await self.resolve_direct_url(video_url)
        except Exception as e:
            logger.error(f"FxTwitter resolution failed: {e}")
        return None

    async def resolve_vxtwitter(self, url: str) -> Optional[Tuple[bytes, str]]:
        """Rewrites to vxtwitter.com for backup extraction."""
        parsed = urlparse(url)
        vx_netloc = parsed.netloc.replace("twitter.com", "vxtwitter.com").replace("x.com", "vxtwitter.com")
        vx_url = parsed._replace(netloc=vx_netloc).geturl()
        
        logger.info(f"VxTwitter redirect request: {vx_url}")
        headers = {"User-Agent": "Mozilla/5.0 (compatible; HelixBot/1.0)"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(vx_url, headers=headers)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    video_meta = soup.find("meta", property="og:video") or soup.find("meta", property="og:video:secure_url")
                    if video_meta and video_meta.get("content"):
                        video_url = video_meta["content"]
                        logger.info(f"VxTwitter extracted video URL: {video_url}")
                        return await self.resolve_direct_url(video_url)
        except Exception as e:
            logger.error(f"VxTwitter resolution failed: {e}")
        return None

    async def resolve_ytdlp(self, url: str) -> Optional[Tuple[bytes, str]]:
        """Invokes yt-dlp to extract stream URL and downloads it."""
        if not self.has_binary("yt-dlp"):
            logger.warning("yt-dlp binary not found in path. Skipping.")
            return None
        
        logger.info(f"Querying yt-dlp for stream url: {url}")
        try:
            # Run yt-dlp to get the direct video stream URL
            cmd = ["yt-dlp", "-g", "-f", "mp4/best", url]
            proc = await subprocess.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0 and stdout:
                stream_url = stdout.decode("utf-8").strip()
                if stream_url:
                    logger.info(f"yt-dlp resolved stream url: {stream_url}")
                    return await self.resolve_direct_url(stream_url)
            else:
                logger.warning(f"yt-dlp returned non-zero code {proc.returncode}: {stderr.decode('utf-8')}")
        except Exception as e:
            logger.error(f"yt-dlp subprocess run failed: {e}")
        return None

    async def resolve_telegram(self, url: str) -> Optional[Tuple[bytes, str]]:
        """Parses Telegram public channel preview pages or posts to resolve video stream."""
        # Standardize URL to public post preview e.g. https://t.me/s/channel/123 or https://t.me/channel/123
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        parts = path.split("/")
        
        if len(parts) >= 2 and parts[-1].isdigit():
            # It is a specific post e.g. t.me/durov/123
            channel = parts[0]
            post_id = parts[1]
            preview_url = f"https://t.me/{channel}/{post_id}?embed=1"
        else:
            # Profile page t.me/durov
            preview_url = f"https://t.me/s/{parts[0]}" if parts else url
            
        logger.info(f"Telegram extraction request: {preview_url}")
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(preview_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Check for video elements or og:video
                    video_meta = soup.find("meta", property="og:video")
                    if video_meta and video_meta.get("content"):
                        return await self.resolve_direct_url(video_meta["content"])
                    
                    video_elem = soup.find("video")
                    if video_elem and video_elem.get("src"):
                        video_src = video_elem["src"]
                        if video_src.startswith("//"):
                            video_src = "https:" + video_src
                        elif video_src.startswith("/"):
                            video_src = "https://t.me" + video_src
                        return await self.resolve_direct_url(video_src)
        except Exception as e:
            logger.error(f"Telegram extraction failed: {e}")
        return None

    async def resolve_reddit(self, url: str) -> Optional[Tuple[bytes, str]]:
        """Queries Reddit JSON API to extract media links."""
        # Convert Reddit post URL to .json API URL
        parsed = urlparse(url)
        json_url = parsed.geturl()
        if not json_url.endswith(".json"):
            # strip trailing slash and add .json
            json_url = json_url.rstrip("/") + ".json"
            
        logger.info(f"Reddit extraction request: {json_url}")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OSINT-Forensics/1.0"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(json_url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    # Reddit response data for posts is typically a list containing the post details
                    if isinstance(data, list) and len(data) > 0:
                        post_data = data[0].get("data", {}).get("children", [{}])[0].get("data", {})
                        
                        # 1. Try secure media
                        media = post_data.get("secure_media") or post_data.get("media")
                        if media and "reddit_video" in media:
                            video_url = media["reddit_video"].get("fallback_url")
                            if video_url:
                                return await self.resolve_direct_url(video_url)
                                
                        # 2. Try previews
                        preview = post_data.get("preview")
                        if preview and "images" in preview:
                            variants = preview["images"][0].get("variants", {})
                            if "mp4" in variants:
                                video_url = variants["mp4"].get("source", {}).get("url")
                                if video_url:
                                    # replace encoded amp;
                                    video_url = video_url.replace("&amp;", "&")
                                    return await self.resolve_direct_url(video_url)
                                    
                        # 3. Fallback to direct URL if it ends with video/image extensions
                        url_field = post_data.get("url")
                        if url_field and any(url_field.lower().endswith(ext) for ext in [".mp4", ".png", ".jpg", ".jpeg", ".webp", ".gif"]):
                            return await self.resolve_direct_url(url_field)
        except Exception as e:
            logger.error(f"Reddit extraction failed: {e}")
        return None

    async def resolve(self, url: str) -> Tuple[bytes, str]:
        """Orchestrates resolution chain."""
        logger.info(f"Resolving media for: {url}")
        
        # 1. Direct url attempt (only if it is formatted like direct link)
        parsed = urlparse(url)
        path = parsed.path.lower()
        if any(path.endswith(ext) for ext in [".mp4", ".png", ".jpg", ".jpeg", ".webp", ".webm", ".gif"]):
            res = await self.resolve_direct_url(url)
            if res:
                return res

        # 2. Provider chain for Twitter/X
        if "twitter.com" in parsed.netloc or "x.com" in parsed.netloc:
            # Attempt FxTwitter
            res = await self.resolve_fxtwitter(url)
            if res:
                return res
            # Attempt VxTwitter
            res = await self.resolve_vxtwitter(url)
            if res:
                return res

        # 3. Telegram
        if "t.me" in parsed.netloc or "telegram" in parsed.netloc:
            res = await self.resolve_telegram(url)
            if res:
                return res

        # 4. Reddit
        if "reddit.com" in parsed.netloc:
            res = await self.resolve_reddit(url)
            if res:
                return res

        # 5. yt-dlp backup for everything
        res = await self.resolve_ytdlp(url)
        if res:
            return res

        # Last direct attempt if nothing else matched
        res = await self.resolve_direct_url(url)
        if res:
            return res

        raise ValueError("media_extraction_failed")
