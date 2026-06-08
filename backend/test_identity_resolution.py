import pytest
from identity_resolution import IdentityResolutionEngine, IdentityResolutionPlugin

def test_username_similarity():
    plugin = IdentityResolutionPlugin("GitHub", "github.com")
    
    # Identical
    assert plugin.calculate_username_similarity("durov", "durov") == 1.0
    assert plugin.calculate_username_similarity("@durov", "durov") == 1.0
    
    # High similarity
    assert plugin.calculate_username_similarity("durov", "durov_dev") >= 0.70
    
    # Completely different
    assert plugin.calculate_username_similarity("durov", "kasamacura") < 0.30

@pytest.mark.anyio
async def test_plugin_registration():
    engine = IdentityResolutionEngine()
    assert len(engine.plugins) >= 5
    platform_names = [p.platform_name for p in engine.plugins]
    assert "GitHub" in platform_names
    assert "LinkedIn" in platform_names
    assert "Telegram" in platform_names
