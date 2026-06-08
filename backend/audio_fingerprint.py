import os
import subprocess
import json
import hashlib
import shutil
import logging

logger = logging.getLogger("helix.audio")

def has_binary(name: str) -> bool:
    """Checks if a binary is available in the system path."""
    return shutil.which(name) is not None

def calculate_audio_hash(video_path: str) -> str:
    """
    Generates a unique audio fingerprint hash for the video.
    Pipeline priority:
    1. Chromaprint (fpcalc) audio fingerprinting.
    2. FFmpeg audio stream extraction and SHA-256 hashing.
    3. Metadata-based pseudo-hash fallback.
    """
    if not os.path.exists(video_path):
        logger.error(f"Video file not found for audio fingerprinting: {video_path}")
        return "Unavailable"

    # 1. Try fpcalc (Chromaprint)
    if has_binary("fpcalc"):
        try:
            logger.info("Extracting Chromaprint using fpcalc...")
            cmd = ["fpcalc", "-json", video_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                fingerprint = data.get("fingerprint")
                if fingerprint:
                    # Hash the long fingerprint string to get a clean 64-character hex hash
                    hasher = hashlib.sha256()
                    hasher.update(fingerprint.encode("utf-8"))
                    logger.info("Chromaprint signature generated successfully.")
                    return hasher.hexdigest()
        except Exception as e:
            logger.warning(f"fpcalc fingerprinting failed: {e}. Moving to FFmpeg fallback.")

    # 2. Try FFmpeg raw stream hashing
    if has_binary("ffmpeg"):
        try:
            logger.info("Extracting raw audio stream via FFmpeg...")
            # Extract mono audio, 11025Hz sample rate, wav container, send to stdout
            cmd = [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-vn",             # No video
                "-ac", "1",        # Mono channel
                "-ar", "11025",    # Sample rate
                "-f", "wav",       # Wav container
                "pipe:1"           # Output to stdout
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=20)
            if result.returncode == 0 and result.stdout:
                hasher = hashlib.sha256()
                hasher.update(result.stdout)
                logger.info("Audio stream extracted and hashed successfully via FFmpeg.")
                return hasher.hexdigest()
        except Exception as e:
            logger.warning(f"FFmpeg audio extraction failed: {e}. Moving to metadata pseudo-hash.")

    # 3. Secure Metadata-based Pseudo-hash Fallback (Disabled in FORENSIC_STRICT_MODE)
    strict_mode = os.getenv("FORENSIC_STRICT_MODE", "true").lower() == "true"
    if strict_mode:
        logger.info("FORENSIC_STRICT_MODE active: pseudo-audio hash generation bypassed.")
        return "Unavailable"
        
    try:
        logger.info("Generating metadata-based pseudo-audio hash...")
        file_size = os.path.getsize(video_path)
        base_name = os.path.basename(video_path)
        # Create a stable hash based on file attributes
        hasher = hashlib.sha256()
        hasher.update(f"{base_name}_{file_size}_audio_pseudohash".encode("utf-8"))
        logger.info("Pseudo-audio hash generated.")
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Fallback pseudo-hash generation failed: {e}")
        return "Unavailable"

