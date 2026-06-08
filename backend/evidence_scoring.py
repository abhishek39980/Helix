import logging
from typing import List, Dict, Any, Tuple
from evidence import Evidence

logger = logging.getLogger("helix.evidence_scoring")

class EvidenceScoringEngine:
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode

    def evaluate_location_confidence(self, evidence_list: List[Evidence]) -> Dict[str, Any]:
        """
        Aggregates location attributions from evidence layers.
        Enforces:
        - 1 active signal/layer -> max 40% confidence
        - 2 active signals/layers -> max 65% confidence
        - 3+ corroborating signals/layers -> 80%+ confidence
        """
        if not evidence_list:
            return {
                "country": "Unknown",
                "confidence": 0.0,
                "classification": "INDETERMINATE",
                "explanation": {
                    "active_layers": 0,
                    "agreement_score": 0.0,
                    "evidence_quality": 0.0,
                    "sources": [],
                    "summary": "No OSINT location evidence found."
                }
            }

        # Group evidence by country value (value can be dict containing 'country' or direct string)
        country_groups: Dict[str, List[Evidence]] = {}
        layer_sources: Dict[str, set] = {}

        for ev in evidence_list:
            country = None
            if isinstance(ev.value, dict) and "country" in ev.value:
                country = ev.value["country"]
            elif isinstance(ev.value, str):
                country = ev.value
                
            if country:
                country_key = country.strip().title()
                country_groups.setdefault(country_key, []).append(ev)
                layer_sources.setdefault(country_key, set()).add(ev.source)

        if not country_groups:
            return {
                "country": "Unknown",
                "confidence": 0.0,
                "classification": "INDETERMINATE",
                "explanation": {
                    "active_layers": 0,
                    "agreement_score": 0.0,
                    "evidence_quality": 0.0,
                    "sources": [],
                    "summary": "No geographic attribution found in evidence."
                }
            }

        # Calculate scores per country
        country_scores = {}
        for country, evs in country_groups.items():
            # Base score = sum of reliability * weight
            base_score = sum(ev.reliability for ev in evs)
            # Corroboration bonus: multiply by 1 + 0.15 for each additional layer
            n_layers = len(layer_sources[country])
            bonus = 1.0 + 0.15 * (n_layers - 1) if n_layers > 1 else 1.0
            country_scores[country] = base_score * bonus

        # Determine winning country
        winning_country = max(country_scores, key=country_scores.get)
        winning_evs = country_groups[winning_country]
        winning_layers = list(layer_sources[winning_country])
        n_winning_layers = len(winning_layers)

        # Count total active layers across all attributed countries
        all_active_layers = set()
        for c, ls in layer_sources.items():
            all_active_layers.update(ls)
        n_active_layers = len(all_active_layers)

        # Calculate evidence quality (average reliability of winning evidence)
        evidence_quality = sum(ev.reliability for ev in winning_evs) / len(winning_evs) if winning_evs else 0.0

        # Calculate agreement score (winning score vs sum of all scores)
        total_score_sum = sum(country_scores.values())
        agreement_score = country_scores[winning_country] / total_score_sum if total_score_sum > 0 else 1.0

        # Raw confidence calculation
        raw_confidence = (country_scores[winning_country] / max(1.0, float(n_active_layers))) * 0.90
        # Project confidence to percentage
        confidence = min(0.99, max(0.10, raw_confidence))

        # Enforce Capping Rules
        capping_reason = ""
        if n_active_layers == 1:
            confidence = min(confidence, 0.40)
            capping_reason = "Capped at 40% max because only 1 active layer detected."
        elif n_active_layers == 2:
            confidence = min(confidence, 0.65)
            capping_reason = "Capped at 65% max because only 2 active layers detected."
        elif n_winning_layers >= 3:
            # Boost confidence for strong corroboration
            confidence = max(confidence, 0.80)
            capping_reason = "Boosted to 80%+ because 3 or more independent layers corroborate this location."

        # Set classification based on confidence
        if confidence >= 0.80:
            classification = "HIGH FORENSIC CREDIBILITY"
        elif confidence >= 0.60:
            classification = "MEDIUM FORENSIC CREDIBILITY"
        else:
            classification = "PROBABLE CORRELATION (LOW CONFIDENCE)"

        summary_explanation = f"Suspected location: {winning_country}. Verified by {n_winning_layers} layers ({', '.join(winning_layers)}). "
        if capping_reason:
            summary_explanation += capping_reason

        return {
            "country": winning_country,
            "confidence": round(confidence, 2),
            "classification": classification,
            "explanation": {
                "active_layers": n_winning_layers,
                "agreement_score": round(agreement_score, 2),
                "evidence_quality": round(evidence_quality, 2),
                "sources": winning_layers,
                "summary": summary_explanation
            }
        }
