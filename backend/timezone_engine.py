import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from evidence import Evidence

logger = logging.getLogger("helix.timezone_engine")

class TimezoneInferenceEngine:
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode

    def parse_timestamp(self, ts_str: str) -> Optional[datetime]:
        if not ts_str:
            return None
        try:
            # Handle Twitter format e.g. "Mon Jun 08 12:00:00 +0000 2026"
            if "+0000" in ts_str or ts_str.endswith("UTC"):
                return datetime.strptime(ts_str.replace(" +0000 ", " "), "%a %b %d %H:%M:%S %Y")
            # Handle ISO format
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            pass
        return None

    def calculate_posting_histogram_offset(self, timestamps: List[str]) -> Optional[Tuple[float, float]]:
        """
        Analyzes UTC hours to find the peak window.
        Returns: inferred_offset (float), peak_pct (float)
        """
        hour_counts = [0] * 24
        parsed_count = 0
        for ts in timestamps:
            dt = self.parse_timestamp(ts)
            if dt:
                hour_counts[dt.hour] += 1
                parsed_count += 1

        if parsed_count < 10:
            return None

        total = sum(hour_counts)
        best_start, best_sum = 0, 0
        # Find 6-hour peak window of activity
        for start in range(24):
            window_sum = sum(hour_counts[(start + h) % 24] for h in range(6))
            if window_sum > best_sum:
                best_sum = window_sum
                best_start = start

        peak_pct = best_sum / total
        utc_midpoint = (best_start + 3) % 24
        # Assume typical peak activity is around 19:00 (7 PM) local time
        local_peak_center = 20.0  # evening peak model
        raw_offset = (local_peak_center - utc_midpoint) % 24
        if raw_offset > 12:
            raw_offset -= 24
            
        return raw_offset, peak_pct

    def scan_timezone_text_signals(self, text: str) -> List[Dict[str, Any]]:
        """Scans bios/posts for explicit timezone or business hour references."""
        signals = []
        if not text:
            return signals

        # 1. Look for GMT/UTC offsets
        m = re.search(r"\b(?:gmt|utc)\s*([+-]\d{1,2}(?::\d{2})?)\b", text, re.IGNORECASE)
        if m:
            offset_str = m.group(1)
            try:
                if ":" in offset_str:
                    h, min_val = offset_str.split(":")
                    offset = float(h) + (float(min_val) / 60.0)
                else:
                    offset = float(offset_str)
                signals.append({
                    "type": "explicit_gmt_text",
                    "offset": offset,
                    "evidence": f"Found explicit timezone offset reference '{m.group(0)}' in text."
                })
            except Exception:
                pass

        # 2. Look for business hour references (e.g. 9am to 6pm JST/IST/EST)
        m_jst = re.search(r"\b(jst|ist|est|pst|cst|gmt|bst|cest|cet)\b", text, re.IGNORECASE)
        if m_jst:
            tz_code = m_jst.group(1).upper()
            tz_offsets = {
                "JST": 9.0, "IST": 5.5, "EST": -5.0, "EDT": -4.0,
                "PST": -8.0, "PDT": -7.0, "CST": -6.0, "CDT": -5.0,
                "GMT": 0.0, "BST": 1.0, "CET": 1.0, "CEST": 2.0
            }
            if tz_code in tz_offsets:
                signals.append({
                    "type": "timezone_code_text",
                    "offset": tz_offsets[tz_code],
                    "evidence": f"Found timezone code '{tz_code}' in text."
                })
        return signals

    def infer_timezone(self, posts: List[Any], bio_text: str, session_id: str) -> Optional[Evidence]:
        """Combines posting histogram, snowflake timestamp, and text signals to infer timezone."""
        evidence_strings = []
        inferred_offset = 0.0
        confidence = 0.0
        
        # 1. Text signals
        text_signals = self.scan_timezone_text_signals(bio_text)
        for p in posts:
            text_signals.extend(self.scan_timezone_text_signals(getattr(p, "full_text", "")))
            
        if text_signals:
            # Take the first matched text signal
            sig = text_signals[0]
            inferred_offset = sig["offset"]
            evidence_strings.append(sig["evidence"])
            confidence = 0.85
            
        # 2. Histogram signals
        post_timestamps = [getattr(p, "created_at", "") for p in posts if getattr(p, "created_at", "")]
        hist_res = self.calculate_posting_histogram_offset(post_timestamps)
        if hist_res:
            hist_offset, peak_pct = hist_res
            if not evidence_strings:
                inferred_offset = hist_offset
                confidence = 0.60 if peak_pct >= 0.40 else 0.40
            evidence_strings.append(f"Posting activity histogram suggests UTC offset {hist_offset:+.1f}h (Peak window captures {peak_pct * 100:.1f}% of posts)")
            
        if not evidence_strings:
            return None

        tz_label = f"UTC {inferred_offset:+.2f}"
        
        return Evidence(
            source="timezone_engine",
            source_type="timezone",
            collection_method="temporal_inference",
            timestamp=datetime.now(timezone.utc).isoformat(),
            reliability=confidence,
            value={
                "offset": inferred_offset,
                "tz_label": tz_label
            },
            metadata={
                "session_id": session_id,
                "evidence_audit": evidence_strings
            }
        )
