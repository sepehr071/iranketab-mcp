import httpx
import pytest
from conftest import fixture, page
from test_iranketab import form

pytestmark = pytest.mark.anyio


async def test_book_extras_awards_series_praise_and_related(client, api):
    api["/book/14161"] = page("extras.html")
    r = (await client.call_tool("ik_book_extras", {"book": "14161", "bio_chars": 100})).structured_content
    assert {"id": 78, "name": "جایزه ی ملی کتاب انگلستان"} in r["awards"]
    assert r["series"] == [{"id": 707, "name": "مجموعه داستان های هری پاتر"}]
    assert {"id": 787, "name": "برترین آثار تبدیل شده به فیلم و سریال"} in r["lists"]
    assert r["features"] and len(r["author_bio"]) <= 100
    assert r["related_books"][0]["book_id"] and r["related_books"][0]["price"] > 0
    api["/book/858"] = page("extras858.html")
    r = (await client.call_tool("ik_book_extras", {"book": "858", "excerpt_chars": 50})).structured_content
    assert {p["source"] for p in r["praise"]} == {"Barnes & Noble", "Guardian", "Penguin Random House"}
    assert len(r["excerpts"]) == 3 and all(len(x) <= 50 for x in r["excerpts"])
    assert r["related_articles"][0]["slug"] == "the-idiot"
    assert any(b["discount_pct"] for b in r["related_books"])


async def test_recommend_posts_ids_and_parses_cards(client, api):
    api["/nextread/suggest"] = fixture("suggest.json")
    r = (
        await client.call_tool("ik_recommend", {"books": ["858", "https://www.iranketab.ir/book/2525-x"]})
    ).structured_content
    req = api.calls[0]
    assert (
        req.method == "POST"
        and req.content.decode().count("ids%5B%5D=") == 2
        and "ids%5B%5D=2525" in req.content.decode()
    )
    assert r["based_on"] == [858, 2525] and r["count"] == 4 and r["suggestions"][0]["title"]
    assert r["suggestions"][0]["price"] > 0
    api["/nextread/suggest"] = {"isSuccess": False, "message": "no", "data": None}
    res = await client.call_tool("ik_recommend", {"books": ["1"]})
    assert res.is_error


async def test_form_posts_send_the_headers_of_the_sites_jquery(client, api):
    api["/nextread/suggest"] = fixture("suggest.json")
    await client.call_tool("ik_recommend", {"books": ["858"]})
    h = api.calls[0].headers
    assert (h["accept"], h["x-requested-with"], h["origin"], h["referer"]) == (
        "application/json, text/javascript, */*; q=0.01",
        "XMLHttpRequest",
        "https://www.iranketab.ir",
        "https://www.iranketab.ir/nextread",
    )
    assert (h["sec-fetch-site"], h["sec-fetch-mode"], h["sec-fetch-dest"], h["priority"]) == (
        "same-origin",
        "cors",
        "empty",
        "u=1, i",
    )
    assert h["content-type"] == "application/x-www-form-urlencoded; charset=UTF-8"


async def test_lists_reads_filter_group(client, api):
    api["/tag/325"] = page("lists.html")
    r = (await client.call_tool("ik_lists", {"kind": "series"})).structured_content
    assert r["kind"] == "series" and r["count"] > 0 and all(isinstance(i["id"], int) for i in r["items"])
    r = (await client.call_tool("ik_lists", {})).structured_content
    assert r["items"][0]["name"].startswith("جایزه")


async def test_articles_list_and_search(client, api):
    api["/blog/filter"] = fixture("blog_filter.json")
    r = (await client.call_tool("ik_articles", {"page": 2})).structured_content
    assert api.calls[0].method == "POST" and api.calls[0].url.params["page"] == "2" and form(api.calls[0]) == {}
    assert r["total"] > 100 and r["pages"] > 1 and r["articles"][0]["slug"] and r["articles"][0]["title_en"]
    api["/result/داستایفسکی"] = page("result_articles.html")
    r = (await client.call_tool("ik_articles", {"query": "داستایفسکی"})).structured_content
    assert api.calls[1].url.params["t"] == "مقاله" and len(r["articles"]) == 3 and r["site_hits"] == 20
    assert r["articles"][0]["slug"] == "dostoevsky-and-the-human-mind"


async def test_article_text_paging_and_missing(client, api):
    api["/blog/crime-and-punishment-analysis"] = page("article.html")
    r = (
        await client.call_tool("ik_article", {"article": "crime-and-punishment-analysis", "max_chars": 500})
    ).structured_content
    assert r["title_en"] == "Crime and Punishment Analysis" and len(r["text"]) == 500 and r["next_offset"] == 500
    assert r["books"][0] == 849 and r["profiles"][0] == 1059
    url = "https://www.iranketab.ir/blog/crime-and-punishment-analysis"
    r2 = (await client.call_tool("ik_article", {"article": url, "max_chars": 500, "offset": 500})).structured_content
    assert r2["text"] and r2["text"] != r["text"]
    api["/blog/nope"] = lambda request: httpx.Response(200, text="<html><body>x</body></html>")
    res = await client.call_tool("ik_article", {"article": "nope"})
    assert res.is_error and "No article" in res.content[0].text


async def test_article_404_becomes_no_article(client, api):
    api["/blog/gone"] = lambda request: httpx.Response(404, text="nf")
    res = await client.call_tool("ik_article", {"article": "gone"})
    assert res.is_error and "No article" in res.content[0].text
