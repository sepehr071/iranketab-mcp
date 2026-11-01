import asyncio

import pytest

pytestmark = [pytest.mark.live, pytest.mark.anyio]

IDIOT = 858  # ابله، داستایفسکی: many translations


@pytest.fixture(autouse=True)
async def be_polite():
    await asyncio.sleep(2)


async def test_live_search_book(client):
    r = (await client.call_tool("ik_search", {"query": "ابله", "limit": 5})).structured_content
    assert any(x["id"] == IDIOT for x in r["results"]), r


async def test_live_search_profile_and_publisher(client):
    r = (await client.call_tool("ik_search", {"query": "داستایفسکی", "kind": "profile", "limit": 5})).structured_content
    assert any(x["id"] == 1059 for x in r["results"]), r
    await asyncio.sleep(2)
    r = (await client.call_tool("ik_search", {"query": "خوارزمی", "kind": "publisher"})).structured_content
    assert any(x["id"] == 35 for x in r["results"]), r


async def test_live_book_and_editions(client):
    r = (await client.call_tool("ik_book", {"book": str(IDIOT), "summary_chars": 200})).structured_content
    assert r["title"] == "ابله" and r["editions_count"] >= 10 and r["reviews_count"] > 100
    await asyncio.sleep(2)
    r = (await client.call_tool("ik_editions", {"book": str(IDIOT), "sort": "rating"})).structured_content
    first = r["editions"][0]
    assert first["votes"] >= 3 and first["translators"] and first["publisher"] and first["pages"] > 100
    ratings = [e["rating"] for e in r["editions"] if e["votes"] >= 3]
    assert ratings == sorted(ratings, reverse=True)


async def test_live_reviews(client):
    r = (await client.call_tool("ik_reviews", {"book": str(IDIOT), "page": 2})).structured_content
    assert r["total"] > 100 and r["page"] == 2 and len(r["comments"]) == 20
    assert r["comments"][0]["text"] and r["comments"][0]["date"].startswith("14")


async def test_live_profile_and_publisher(client):
    r = (await client.call_tool("ik_profile", {"profile": "3891"})).structured_content
    assert r["name"] == "مهری آهی" and r["total"] >= 1 and r["books"][0]["book_id"]
    await asyncio.sleep(2)
    r = (await client.call_tool("ik_publisher_books", {"publisher": "35"})).structured_content
    assert r["name"] == "خوارزمی" and r["total"] > 50 and len(r["books"]) == 18


async def test_live_browse_bestsellers_and_filters(client):
    r = (await client.call_tool("ik_browse", {"category": "209"})).structured_content
    assert r["total"] > 100 and len(r["books"]) == 24 and r["books"][0]["price"] > 0
    await asyncio.sleep(2)
    plain = (await client.call_tool("ik_browse", {"category": "103"})).structured_content["total"]
    await asyncio.sleep(2)
    russian = (await client.call_tool("ik_browse", {"category": "103", "filters": ["17=152"]})).structured_content
    assert 0 < russian["total"] < plain


async def test_live_categories(client):
    r = (await client.call_tool("ik_categories", {})).structured_content
    assert any(c["id"] == 209 for c in r["categories"])
    await asyncio.sleep(2)
    r = (await client.call_tool("ik_categories", {"category": "103"})).structured_content
    assert any(g["group"] == 17 for g in r["filter_groups"])


async def test_live_book_extras_and_series(client):
    r = (await client.call_tool("ik_book_extras", {"book": "14161", "bio_chars": 100})).structured_content
    assert any(a["id"] == 78 for a in r["awards"]) and r["series"][0]["id"] == 707 and r["related_books"]
    await asyncio.sleep(2)
    r = (await client.call_tool("ik_book_extras", {"book": str(IDIOT)})).structured_content
    assert {p["source"] for p in r["praise"]} >= {"Guardian"} and r["excerpts"] and r["related_articles"]
    await asyncio.sleep(2)
    r = (await client.call_tool("ik_search", {"query": "هری پاتر", "kind": "category"})).structured_content
    assert any(x["id"] == 707 for x in r["results"]), r


async def test_live_recommend(client):
    r = (await client.call_tool("ik_recommend", {"books": [str(IDIOT), "849", "15810"]})).structured_content
    assert r["count"] >= 10 and all(s["book_id"] and s["price"] for s in r["suggestions"])


async def test_live_lists_and_award_browse(client):
    r = (await client.call_tool("ik_lists", {"kind": "awards"})).structured_content
    assert r["count"] >= 40 and any(i["id"] == 16 for i in r["items"])
    await asyncio.sleep(2)
    r = (await client.call_tool("ik_browse", {"category": "325", "filters": ["15=16"]})).structured_content
    assert r["total"] >= 1 and r["books"][0]["discount_pct"] == 30


async def test_live_articles(client):
    r = (await client.call_tool("ik_articles", {"query": "داستایفسکی", "limit": 5})).structured_content
    assert any(a["slug"] == "crime-and-punishment-analysis" for a in r["articles"]), r
    await asyncio.sleep(2)
    r = (await client.call_tool("ik_articles", {"page": 2})).structured_content
    assert r["total"] > 500 and len(r["articles"]) == 18
    await asyncio.sleep(2)
    r = (
        await client.call_tool("ik_article", {"article": "crime-and-punishment-analysis", "max_chars": 800})
    ).structured_content
    assert r["title_en"] == "Crime and Punishment Analysis" and len(r["text"]) == 800 and r["next_offset"] == 800
