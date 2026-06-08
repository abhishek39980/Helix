import time
import logging
from typing import Dict, List, Any

logger = logging.getLogger("helix.provider_health")

class ProviderStats:
    def __init__(self, name: str):
        self.name = name
        self.success_count = 0
        self.failure_count = 0
        self.total_latency = 0.0
        self.last_success_time = 0.0

    @property
    def total_requests(self) -> int:
        return self.success_count + self.failure_count

    @property
    def success_rate(self) -> float:
        total = self.total_requests
        if total == 0:
            return 1.0  # assume healthy initially
        return self.success_count / total

    @property
    def failure_rate(self) -> float:
        return 1.0 - self.success_rate

    @property
    def average_latency(self) -> float:
        if self.success_count == 0:
            return 0.0
        return self.total_latency / self.success_count

    def record_success(self, latency: float):
        self.success_count += 1
        self.total_latency += latency
        self.last_success_time = time.time()

    def record_failure(self):
        self.failure_count += 1


class ProviderHealthRegistry:
    def __init__(self):
        # Maps category (e.g. "ocr", "media_resolver", "geocoding", "profile", "reverse_search") -> provider_name -> ProviderStats
        self.registry: Dict[str, Dict[str, ProviderStats]] = {}

    def get_stats(self, category: str, provider: str) -> ProviderStats:
        category_dict = self.registry.setdefault(category, {})
        if provider not in category_dict:
            category_dict[provider] = ProviderStats(provider)
        return category_dict[provider]

    def record_success(self, category: str, provider: str, latency: float):
        stats = self.get_stats(category, provider)
        stats.record_success(latency)
        logger.info(f"Recorded success for category '{category}' provider '{provider}' in {latency:.3f}s. Success rate: {stats.success_rate * 100:.1f}%")

    def record_failure(self, category: str, provider: str):
        stats = self.get_stats(category, provider)
        stats.record_failure()
        logger.warning(f"Recorded failure for category '{category}' provider '{provider}'. Success rate: {stats.success_rate * 100:.1f}%")

    def get_prioritized_providers(self, category: str, available_providers: List[str]) -> List[str]:
        """Returns list of providers sorted by success rate (highest first) and latency (lowest first)."""
        stats_list = []
        for p in available_providers:
            stats = self.get_stats(category, p)
            # Penalize heavily if failures are high
            score = stats.success_rate
            # Secondary sorting: average latency
            latency = stats.average_latency
            stats_list.append((p, score, latency))

        # Sort: highest success score first, then lowest latency
        sorted_providers = sorted(stats_list, key=lambda x: (-x[1], x[2]))
        return [item[0] for item in sorted_providers]

    def get_all_health_report(self) -> Dict[str, Any]:
        report = {}
        for category, providers in self.registry.items():
            report[category] = {}
            for name, stats in providers.items():
                report[category][name] = {
                    "success_rate": stats.success_rate,
                    "failure_rate": stats.failure_rate,
                    "average_latency": stats.average_latency,
                    "last_success": stats.last_success_time,
                    "total_requests": stats.total_requests
                }
        return report

# Global health registry instance
health_registry = ProviderHealthRegistry()
