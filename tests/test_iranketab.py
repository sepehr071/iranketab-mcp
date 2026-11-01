import urllib.parse

import httpx
import pytest
from conftest import fixture, page

pytestmark = pytest.mark.anyio

TOOLS = {
    "ik_search",
    "ik_book",
    "ik_editions",
    "ik_reviews",
    "ik_profile",
    "ik_publisher_books",
    "ik_browse",
    "ik_categories",
    "ik_book_extras",
    "ik_recommend",
    "ik_lists",
    "ik_articles",
    "ik_article",
}


def form(request: httpx.Request) -> dict[str, str]:
    return dict(urllib.parse.parse_qsl(request.content.decode()))


async def test_all_tools_are_read_only_and_described(client):
    tools = (await client.list_tools()).tools
    assert {t.name for t in tools} == TOOLS
    for t in tools:
        assert t.annotations.read_only_hint is True, t.name
        assert t.title and t.description.splitlines()[0].endswith("."), t.name
        assert "title" not in str(t.input_schema.get("properties", {}).values()), t.name


async def test_search_lists_each_work_once_with_edition_count(client, api):
    api["/result/ابله"] = page("result.html")  # httpx decodes the path before matching
    r = (await client.call_tool("ik_search", {"query": "ابله", "limit": 5})).structured_content
    first = r["results"][0]
    assert first["id"] == 858 and first["name"] == "ابله" and first["author"] == "فئودور داستایفسکی"
    assert first["matching_editions"] >= 2
    assert len({x["id"] for x in r["results"]}) == len(r["results"])
    assert api.calls[0].url.params["t"] == "کتاب"


async def test_book_lists_editions_with_prices_and_stock(client, api):
    api["/book/858"] = page("book.html")
    r = (await client.call_tool("ik_book", {"book": "858", "summary_chars": 100})).structured_content
    assert r["title"] == "ابله" and r["title_en"] == "The Idiot" and r["authors"][0]["id"] == 1059
    assert r["reviews_count"] == 195 and r["editions_count"] == 4
    ed = {e["edition_id"]: e for e in r["editions"]}
    assert ed[858]["translators"] == ["سروش حبیبی"] and ed[858]["publisher"] == "نشر چشمه"
    assert (ed[858]["price"], ed[858]["list_price"], ed[858]["discount_pct"]) == (2090000, 2200000, 5)
    assert ed[858]["rating"] == 4.17 and ed[858]["votes"] == 82 and ed[858]["in_stock"] is True
    assert ed[2207]["in_stock"] is False and ed[2207].get("list_price") is None
    assert ed[76727]["subtitle"] == "(چرم،لب طلایی)"
    assert r["in_stock_count"] == 3 and r["cheapest_in_stock"] == 1080000
    assert r["best_rated_edition"]["edition_id"] == 858  # 2207 has 4.75 but only 2 votes
    assert len(r["summary"]) <= 100 and "ابله" in r["summary"]


async def test_editions_sort_filter_and_details(client, api):
    api["/book/858"] = page("book.html")
    r = (
        await client.call_tool("ik_editions", {"book": "858", "sort": "price", "in_stock_only": True})
    ).structured_content
    assert [e["edition_id"] for e in r["editions"]] == [76727, 858, 14781]
    top = r["editions"][1]
    assert (top["pages"], top["year_shamsi"], top["isbn"], top["cover"], top["print_no"]) == (
        774,
        1405,
        "978-964-362-211-4",
        "جلد سخت",
        44,
    )
    assert top["translators"] == [{"id": 192, "name": "سروش حبیبی"}] and top["stock"] == "10+"
    r = (await client.call_tool("ik_editions", {"book": "858", "translator": "آهی"})).structured_content
    assert [e["edition_id"] for e in r["editions"]] == [14781]
    r = (await client.call_tool("ik_editions", {"book": "858"})).structured_content
    assert r["editions"][0]["edition_id"] == 858  # best rating among editions with 3+ votes


async def test_book_url_and_missing_book(client, api):
    api["/book/858"] = page("book.html")
    r = (
        await client.call_tool("ik_book", {"book": "https://www.iranketab.ir/book/858-the-idiot#pts=858"})
    ).structured_content
    assert r["book_id"] == 858
    api["/book/5"] = lambda request: httpx.Response(200, text="<html><body>nothing</body></html>")
    res = await client.call_tool("ik_book", {"book": "5"})
    assert res.is_error and "No book with id 5" in res.content[0].text
    res = await client.call_tool("ik_book", {"book": "the idiot"})
    assert res.is_error and "not a book id" in res.content[0].text


async def test_reviews_post_with_site_form_and_clean_dates(client, api):
    api["/comment/list"] = fixture("comments.json")
    r = (await client.call_tool("ik_reviews", {"book": "858", "page": 3, "max_chars": 100})).structured_content
    req = api.calls[0]
    assert (
        req.method == "POST"
        and req.url.params["lvc-page"] == "3"
        and form(req) == {"Type": "Product", "EntityId": "858"}
    )
    assert req.headers["x-requested-with"] == "XMLHttpRequest"
    assert r["total"] == 195 and r["pages"] == 10 and r["page"] == 3
    c = r["comments"][0]
    assert c["replies"] and len(c["text"]) <= 100 and len(c["date"]) == 10 and c["date"][4] == "/"


async def test_profile_reads_bio_and_posts_list_filter(client, api):
    api["/profile/1059"] = page("profile.html")
    api["/profile/filter"] = fixture("tag_filter.json")
    r = (
        await client.call_tool("ik_profile", {"profile": "1059", "sort": "bestselling", "term": "ابله"})
    ).structured_content
    assert r["name"] == "فئودور داستایفسکی" and r["name_en"] == "Fyodor Dostoevsky" and r["bio"].startswith("فئودور")
    req = api.calls[1]
    assert form(req) == {"Id": "1059"} and req.url.params["sort"] == "MostSale" and req.url.params["term"] == "ابله"
    b = r["books"][0]
    assert b["book_id"] == 1045 and b["edition_id"] == 1045 and b["price"] == 179100 and b["discount_pct"] == 10
    assert r["total"] == 546 and r["pages"] == 23


async def test_publisher_books(client, api):
    api["/publisher/35"] = page("publisher.html")
    api["/brand/filter"] = fixture("tag_filter.json")
    r = (await client.call_tool("ik_publisher_books", {"publisher": "35"})).structured_content
    assert r["name"] == "خوارزمی" and r["publisher_id"] == 35 and len(r["books"]) == 3
    assert api.calls[1].url.params["sort"] == "MostSale"  # bestselling by default


async def test_browse_sends_site_filter_params(client, api):
    api["/tag/filter"] = fixture("tag_filter.json")
    r = (
        await client.call_tool("ik_browse", {"category": "103", "filters": ["17=152", "17=29", "183=182"], "page": 2})
    ).structured_content
    q = api.calls[0].url.params
    assert q.get_list("tags-17") == ["152", "29"] and q["tags-183"] == "182" and q["page"] == "2"
    assert form(api.calls[0]) == {"Id": "103"} and r["category_id"] == 103 and len(r["books"]) == 3
    res = await client.call_tool("ik_browse", {"category": "103", "filters": ["Russian"]})
    assert res.is_error and "Bad filter" in res.content[0].text


async def test_categories_menu_and_filter_groups(client, api):
    api["/"] = page("home.html")
    r = (await client.call_tool("ik_categories", {})).structured_content
    assert {"id": 284, "name": "کتاب\u200cها"} in r["categories"]
    api["/tag/103"] = page("tag.html")
    r = (await client.call_tool("ik_categories", {"category": "103"})).structured_content
    groups = {g["group"]: g for g in r["filter_groups"]}
    assert groups[17]["label"] == "ادبیات ملل" and groups[17]["options_count"] > 0
    one = (await client.call_tool("ik_categories", {"category": "103", "group": 17})).structured_content
    assert [g["group"] for g in one["filter_groups"]] == [17]


async def test_blocked_request_gives_actionable_error(client, api):
    api["/book/858"] = lambda request: httpx.Response(403, text="blocked")
    res = await client.call_tool("ik_book", {"book": "858"})
    assert res.is_error and "IRANKETAB_MCP_PROXY" in res.content[0].text
