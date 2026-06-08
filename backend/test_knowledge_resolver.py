import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from knowledge_resolver import KnowledgeResolver

@pytest.mark.anyio
async def test_wikidata_resolution():
    resolver = KnowledgeResolver()
    
    # Mock HTTP responses for Wikidata search and get details (using MagicMock for synchronous json/status_code)
    mock_search_resp = MagicMock()
    mock_search_resp.status_code = 200
    mock_search_resp.json.return_value = {
        "search": [
            {
                "id": "Q20084347",
                "label": "Edomae Sushi",
                "description": "Traditional Tokyo style sushi in Japan"
            }
        ]
    }
    
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {
        "entities": {
            "Q20084347": {
                "claims": {
                    "P17": [
                        {
                            "mainsnak": {
                                "datavalue": {
                                    "value": {
                                        "id": "Q17"
                                    }
                                }
                            }
                        }
                    ],
                    "P625": [
                        {
                            "mainsnak": {
                                "datavalue": {
                                    "value": {
                                        "latitude": 35.6762,
                                        "longitude": 139.6503
                                    }
                                }
                            }
                        }
                    ]
                }
            }
        }
    }
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_search_resp, mock_get_resp]
        res = await resolver.resolve_wikidata("Edomae Sushi")
        
        assert res is not None
        assert res["country"] == "Japan"
        assert res["coordinates"] == [35.6762, 139.6503]
        assert res["source"] == "Wikidata"

@pytest.mark.anyio
async def test_osm_nominatim_resolution():
    resolver = KnowledgeResolver()
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "lat": "35.6895",
            "lon": "139.6917",
            "address": {
                "country": "Japan",
                "city": "Tokyo"
            }
        }
    ]
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        res = await resolver.resolve_openstreetmap("Tokyo Station")
        
        assert res is not None
        assert res["country"] == "Japan"
        assert res["coordinates"] == [35.6895, 139.6917]
        assert res["source"] == "OpenStreetMap"
