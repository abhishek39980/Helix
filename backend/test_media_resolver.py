import pytest
from media_resolver import MediaResolver

@pytest.mark.anyio
async def test_magic_byte_validation():
    resolver = MediaResolver(strict_mode=True)
    
    # Valid PNG bytes
    png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
    assert resolver.validate_magic_bytes(png_bytes) is True
    
    # Valid JPEG bytes
    jpeg_bytes = b'\xff\xd8\xff\xe0\x00\x10JFIF'
    assert resolver.validate_magic_bytes(jpeg_bytes) is True
    
    # Valid GIF bytes
    gif_bytes = b'GIF89a\x01\x00\x01\x00'
    assert resolver.validate_magic_bytes(gif_bytes) is True

    # Valid MP4 bytes (offset 4 has ftyp)
    mp4_bytes = b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00'
    assert resolver.validate_magic_bytes(mp4_bytes) is True

    # Invalid bytes
    assert resolver.validate_magic_bytes(b'invalid_bytes_here') is False
    assert resolver.validate_magic_bytes(b'<html lang="en">') is False

@pytest.mark.anyio
async def test_mime_and_size_validation():
    resolver = MediaResolver(strict_mode=True)
    
    # Size check
    huge_bytes = b'\x00' * (251 * 1024 * 1024)
    valid, reason = resolver.validate_mime_and_size(huge_bytes, "video/mp4")
    assert valid is False
    assert reason == "file_too_large"

    # HTML rejection
    html_bytes = b'<!doctype html><html><body>Error</body></html>'
    valid, reason = resolver.validate_mime_and_size(html_bytes, "text/html")
    assert valid is False
    assert reason == "rejected_html_content"

@pytest.mark.anyio
async def test_strict_mode_blocks_fallback():
    resolver = MediaResolver(strict_mode=True)
    # Since we are in strict mode and there is no direct connection/file, it should fail instead of returning sample video
    with pytest.raises(ValueError) as exc:
        await resolver.resolve("https://x.com/invalid_user/status/123456789")
    assert "media_extraction_failed" in str(exc.value)
