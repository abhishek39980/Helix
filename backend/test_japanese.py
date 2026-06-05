import os
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')
os.environ["PYTHONIOENCODING"] = "utf-8"

# Add backend directory to path
sys.path.insert(0, r"c:\Users\abhis\OneDrive\Desktop\Pi-Labs\Searchengine\backend")

import backend
from backend import run_location_intelligence

async def _test_japanese_pipeline_async():
    # 1. Test case: Japanese bio only (@kasamacura)
    backend._TWITTER_CACHE["kasamacura"] = {
        "profile": {
            "display_name": "かさまくら",
            "description": "“肩肘張らずに、本物を。” 江戸前寿司の伝統を大切にしながら...",
            "location": "",
            "url": "https://x.com/kasamacura"
        },
        "tweets": [],
        "tweet_source": "scrapebadger"
    }

    # 2. Test case: Japanese tweets only
    backend._TWITTER_CACHE["japanese_tweets"] = {
        "profile": {
            "display_name": "English User",
            "description": "Just another profile",
            "location": "",
            "url": "https://x.com/japanese_tweets"
        },
        "tweets": [
            {"full_text": "こんにちは、日本の美味しいラーメンを食べました！", "lang": "ja"}
        ],
        "tweet_source": "nitter"
    }

    # 3. Test case: Japanese bio + empty location
    backend._TWITTER_CACHE["japanese_bio_empty_loc"] = {
        "profile": {
            "display_name": "Sato",
            "description": "東京で開発をしています。よろしくお願いします。",
            "location": "",
            "url": "https://x.com/japanese_bio_empty_loc"
        },
        "tweets": [],
        "tweet_source": "scrapebadger"
    }

    # 4. Test case: Mixed English/Japanese profile
    backend._TWITTER_CACHE["mixed_profile"] = {
        "profile": {
            "display_name": "Taro English",
            "description": "Software engineer learning Japanese / 東京で英語と日本語の勉強をしています。",
            "location": "",
            "url": "https://x.com/mixed_profile"
        },
        "tweets": [
            {"full_text": "This is an English tweet.", "lang": "en"},
            {"full_text": "こちらは日本語のツイートです。", "lang": "ja"}
        ],
        "tweet_source": "nitter"
    }

    cases = [
        ("kasamacura", "https://x.com/kasamacura"),
        ("japanese_tweets", "https://x.com/japanese_tweets"),
        ("japanese_bio_empty_loc", "https://x.com/japanese_bio_empty_loc"),
        ("mixed_profile", "https://x.com/mixed_profile"),
    ]

    all_passed = True
    for username, url in cases:
        print(f"\n========================================================")
        print(f"Testing @{username} ...")
        print(f"========================================================")
        
        result = await run_location_intelligence(username, url)
        
        print(f"Country:    {result['country']}")
        print(f"Confidence: {result['confidence']:.2f} ({int(result['confidence'] * 100)}%)")
        print(f"Evidence:")
        for ev in result['evidence']:
            print(f"  - {ev}")
            
        # Assertions
        try:
            assert result['country'] == "Japan", f"Expected Japan, got {result['country']}"
            assert result['confidence'] >= 0.70, f"Expected confidence > 70%, got {result['confidence']}"
            if username == "kasamacura":
                assert any("Edomae sushi terminology" in ev for ev in result['evidence']), "Missing Edomae sushi terminology evidence"
                assert any("Japanese script detected in bio" in ev for ev in result['evidence']), "Missing script detection evidence in bio"
            print(f"\n>>> SUCCESS: @{username} passed all assertions!")
        except AssertionError as e:
            print(f"\n>>> FAILURE: @{username} failed assertion: {e}")
            all_passed = False

    if all_passed:
        print("\nAll Japanese script location intelligence tests PASSED successfully!")
    else:
        print("\nSome tests FAILED.")
        raise AssertionError("Some location intelligence tests failed.")

def test_japanese_pipeline():
    import asyncio
    asyncio.run(_test_japanese_pipeline_async())

if __name__ == "__main__":
    try:
        test_japanese_pipeline()
        sys.exit(0)
    except AssertionError:
        sys.exit(1)
