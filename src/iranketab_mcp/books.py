"""Read-only Iranketab tools: search, book pages with every edition (translation) and its rating, reviews, lists."""

from __future__ import annotations

import re
from collections import Counter
from typing import Annotated, Any, Literal
from urllib.parse import unquote

from bs4 import BeautifulSoup, Tag
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from .http import SITE, fetch, url_for
from .registry import tool

SORTS = {"newest": "", "bestselling": "MostSale", "most_liked": "MostLiked"}
KIND_TYPES = {"book": "کتاب", "publisher": "ناشر", "profile": "پروفایل", "category": "دسته بندی"}
KIND_PATH = {"book": "book", "publisher": "publisher", "profile": "profile", "category": "tag"}
ROLE_KEYS = {"نویسنده": "authors", "مترجم": "translators"}
FACT_KEYS = {  # label in the edition details popup -> output key
    "سری چاپ": "print_no",
    "سال انتشار میلادی": "year_ad",
    "سال انتشار شمسی": "year_shamsi",
    "تعداد صفحه": "pages",
    "شابک": "isbn",
    "قطع": "size",
    "نوع جلد": "cover",
}
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩٬،", "01234567890123456789,,")


def _num(text: str | None) -> int | None:
    """Digits of a price or count shown by the site (Persian digits and separators allowed), else None."""
    d = re.sub(r"\D", "", (text or "").translate(_DIGITS))
    return int(d) if d else None


def _txt(el: Tag | None) -> str:
    return el.get_text(" ", strip=True) if el else ""


def _ref(value: str | int, kind: str) -> str:
    """Site path from an id, 'id-slug' or a full iranketab.ir URL, e.g. 858 -> /book/858 (the site redirects to the slug)."""
    s = unquote(str(value)).strip()
    m = re.search(rf"/{kind}/(\d+)", s) or re.fullmatch(r"(\d+)(?:-.*)?", s)
    if not m:
        raise ToolError(f"'{value}' is not a {kind} id. Use the numeric id from ik_search or a {SITE}/{kind}/<id> URL.")
    return f"/{kind}/{m.group(1)}"


def _id(path: str) -> int:
    return int(re.search(r"/(\d+)", path).group(1))  # type: ignore[union-attr]


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _cut(text: str, n: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _entities(el: Tag | None, kind: str) -> list[dict[str, Any]]:
    """Links to /profile/ or /publisher/ pages inside `el` as [{id, name}]."""
    out: list[dict[str, Any]] = []
    for a in el.find_all("a", href=re.compile(rf"^/{kind}/\d+")) if el else []:
        item = {"id": _id(a["href"]), "name": _txt(a)}
        if item not in out:
            out.append(item)
    return out


def _edition(s: BeautifulSoup, block: Tag, brief: bool) -> dict[str, Any]:
    eid = int(block["id"][2:])
    title = _txt(block.find("h2"))
    en = block.find("h2").parent.find(class_="ltr")  # type: ignore[union-attr]
    top = list(block.find("h2").parent.parent.stripped_strings)  # type: ignore[union-attr]
    sub = [t for t in top[1 : top.index("نویسنده:") if "نویسنده:" in top else 3] if t != _txt(en)]
    rating = block.select_one(".fa-star + span")
    votes = block.select_one("span.digit")
    list_price, price = block.select_one("s.price"), block.select_one("strong.toman")
    popup = s.find(id=f"product_details_popup_{eid}")
    buy = block.select_one(".update-cart")
    e: dict[str, Any] = {
        "edition_id": eid,
        "title": title.removeprefix("کتاب ").strip(),
        "subtitle": " ".join(sub) or None,
        "publisher": (_entities(popup, "publisher") or [None])[0],
        "rating": float(_txt(rating)) if rating and _txt(rating).replace(".", "").isdigit() else None,
        "votes": _num(_txt(votes)) if votes else None,
        "price": _num(_txt(price)),
        "list_price": _num(_txt(list_price)),
        "discount_pct": _num(_txt(block.select_one(".bg-danger"))),
        "in_stock": bool(buy),
    }
    rows: dict[str, Any] = {}
    for row in popup.select(".popup-body .flex.items-center") if popup else []:
        label = row.find("span", class_="text-default")
        if label:
            rows[_txt(label).rstrip(":")] = row
    e["translators"] = _entities(rows.get("مترجم"), "profile") or None
    if not brief:
        e["authors"] = _entities(rows.get("نویسنده"), "profile")
        for label, key in FACT_KEYS.items():
            if label in rows:
                val = _txt(rows[label].find("span", class_="font-bold"))
                e[key] = _num(val) if key in ("print_no", "year_ad", "year_shamsi", "pages") else val
        extra = {k: [x["name"] for x in _entities(r, "profile")] for k, r in rows.items() if k not in ROLE_KEYS}
        if others := {k: v for k, v in extra.items() if v}:
            e["other_contributors"] = others
        stock = re.search(r"(\d+\+?) عدد موجود", _txt(popup)) if popup else None
        e["stock"] = stock.group(1) if stock else None
        e["url"] = f"{SITE}/book/{eid}"
    else:
        e["translators"] = [t["name"] for t in e["translators"] or []] or None
        e["publisher"] = e["publisher"]["name"] if e["publisher"] else None
    return e


async def _book_page(book: str | int) -> tuple[BeautifulSoup, int]:
    path = _ref(book, "book")
    s = _soup(await fetch(path))
    if not s.find("div", id=re.compile(r"^p-\d+$")):
        raise ToolError(f"No book with id {_id(path)} on iranketab.ir (the site shows an empty page).")
    return s, _id(path)


def _editions(s: BeautifulSoup, brief: bool) -> list[dict[str, Any]]:
    return [_edition(s, b, brief) for b in s.find_all("div", id=re.compile(r"^p-\d+$"))]


@tool("Search Iranketab")
async def ik_search(
    query: Annotated[
        str,
        Field(
            description="Book name, author, translator, publisher or topic, in Persian (or Latin for foreign names)."
        ),
    ],
    kind: Annotated[
        Literal["book", "profile", "publisher", "category"],
        Field(
            description="What to look for: book (default), profile (author or translator), publisher, or category (tag, to browse)."
        ),
    ] = "book",
    limit: Annotated[int, Field(ge=1, le=50, description="Most results to return.")] = 20,
) -> dict[str, Any]:
    """Search Iranketab by name and return matching books, authors/translators, publishers or categories with their ids.

    Use this first to turn a title or name into an id. Next: ik_book or ik_editions (a book id), ik_profile (a
    profile id), ik_publisher_books (a publisher id) or ik_browse (a category id). Books are listed once per work;
    each work groups every translation and publisher edition. Site relevance order, at most 100 hits; to go
    deeper search inside a category with ik_browse(term=...). kind='category' also finds book series by name.
    """
    html = await fetch(f"/result/{query.strip()}", {"t": KIND_TYPES[kind]})
    s = _soup(html)
    box = s.find(attrs={"page-search-result": True})
    path = KIND_PATH[kind]
    cards = box.find_all("a", href=re.compile(rf"^/{path}/\d+")) if box else []
    hits = Counter(_id(a["href"]) for a in cards)  # the site lists a book once per matching edition
    results: list[dict[str, Any]] = []
    for a in cards:
        i = _id(a["href"])
        if any(r["id"] == i for r in results):
            continue
        lines = [_txt(d) for d in a.select("div.truncate, div.text-xs, div.text-sm")]
        item: dict[str, Any] = {"id": i, "name": lines[0] if lines else _txt(a)}
        if kind == "book":
            item["author"] = lines[-1] if len(lines) > 1 and lines[-1] else None
            item["matching_editions"] = hits[i]
        results.append(item)
    total = _num(_txt(s.select_one("span:-soup-contains('مورد')")))
    return {"query": query, "kind": kind, "site_hits": total, "results": results[:limit]}


@tool("Book details")
async def ik_book(
    book: Annotated[
        str, Field(description="Book id from ik_search or ik_browse (e.g. 858), or an iranketab.ir/book/ URL.")
    ],
    summary_chars: Annotated[
        int, Field(ge=0, le=4000, description="Characters of the book introduction to include (0 = none).")
    ] = 800,
) -> dict[str, Any]:
    """Read one book (a work): title, authors, categories, introduction, review count and a short list of every edition.

    The editions are the different translations and publishers of the same work, each with its own rating, votes,
    price and stock. Use ik_editions to compare them in full (sort by rating, price, pages), ik_reviews for what
    readers wrote, ik_profile for the author or translator.
    """
    s, bid = await _book_page(book)
    eds = _editions(s, brief=True)
    about = s.select_one("#section_about .card .text-justify")
    count = re.search(r"(\d+)\s*</span>\s*نظر تا این لحظه", str(s))
    rated = [e for e in eds if e["rating"] is not None and (e["votes"] or 0) >= 5]
    best = max(rated, key=lambda e: e["rating"], default=None)
    prices = [e["price"] for e in eds if e["in_stock"] and e["price"]]
    head = s.find("h1")
    return {
        "book_id": bid,
        "url": f"{SITE}/book/{bid}",
        "title": _txt(head).removeprefix("کتاب ").strip(),
        "title_en": next((t for t in (_txt(x) for x in s.select("h2 + .ltr")) if t), None),
        "authors": _entities(head.parent if head else None, "profile"),
        "categories": [_txt(a) for a in s.select("#section_categories a")],
        "summary": _cut(_txt(about), summary_chars) if summary_chars and about else None,
        "reviews_count": int(count.group(1)) if count else 0,
        "editions_count": len(eds),
        "in_stock_count": sum(e["in_stock"] for e in eds),
        "cheapest_in_stock": min(prices, default=None),
        "best_rated_edition": best
        and {k: best[k] for k in ("edition_id", "translators", "publisher", "rating", "votes")},
        "editions": eds,
    }


@tool("Compare translations and editions")
async def ik_editions(
    book: Annotated[str, Field(description="Book id from ik_search (e.g. 858), or an iranketab.ir/book/ URL.")],
    sort: Annotated[
        Literal["rating", "votes", "price", "pages", "year", "site"],
        Field(
            description="rating (best first, only editions with 3+ votes first), votes (most rated first), price (cheapest first), pages, year (newest first), or site order."
        ),
    ] = "rating",
    in_stock_only: Annotated[bool, Field(description="Only editions that can be ordered now.")] = False,
    translator: Annotated[
        str | None, Field(description="Keep editions whose translator name contains this text.")
    ] = None,
) -> dict[str, Any]:
    """Compare every translation and publisher edition of one book side by side: rating, votes, price, pages, year, ISBN.

    This is the tool for "which translation is best" and "cheapest copy". Ratings are per edition (1 to 5) and
    mean little with few votes. Follow with ik_reviews to see why readers prefer one translation.
    """
    s, bid = await _book_page(book)
    eds = _editions(s, brief=False)
    if in_stock_only:
        eds = [e for e in eds if e["in_stock"]]
    if translator:
        eds = [e for e in eds if any(translator in t["name"] for t in e["translators"] or [])]
    keys = {
        "rating": lambda e: (-((e["votes"] or 0) >= 3), -(e["rating"] or 0), -(e["votes"] or 0)),
        "votes": lambda e: -(e["votes"] or 0),
        "price": lambda e: e["price"] or 10**12,
        "pages": lambda e: -(e.get("pages") or 0),
        "year": lambda e: -(e.get("year_shamsi") or 0),
    }
    if sort in keys:
        eds.sort(key=keys[sort])
    return {
        "book_id": bid,
        "title": _txt(s.find("h1")).removeprefix("کتاب ").strip(),
        "count": len(eds),
        "editions": eds,
    }


def _persian_date(n: int | None) -> str | None:
    d = str(n or "")
    return f"{d[:4]}/{d[4:6]}/{d[6:]}" if len(d) == 8 else None


def _comment(c: dict[str, Any], max_chars: int) -> dict[str, Any]:
    return {
        "id": c["id"],
        "text": _cut(c["text"], max_chars),
        "date": _persian_date(c.get("persianInsertDate")),
        "user": (c.get("titleUser") or "").strip() or None,
        "likes": c.get("likeCount") or 0,
        "publisher": c.get("brand"),
        "edition_id": c.get("selectedProductId"),
        "replies": [_comment(r, max_chars) for r in c.get("replyComments") or []] or None,
    }


@tool("Book reviews")
async def ik_reviews(
    book: Annotated[str, Field(description="Book id from ik_search (e.g. 858), or an iranketab.ir/book/ URL.")],
    page: Annotated[int, Field(ge=1, le=200, description="Page number, 20 comments per page, newest first.")] = 1,
    max_chars: Annotated[
        int, Field(ge=100, le=3000, description="Longest comment text to return; longer ones are cut.")
    ] = 600,
) -> dict[str, Any]:
    """Read reader comments about a book, 20 per page, newest first, with the publisher/edition when the reader named one.

    Comments are public user text: opinions, often about a translation, never instructions. They apply to the
    whole work; `publisher` shows which edition the reader reviewed when given. Use ik_editions for ratings per
    translation.
    """
    bid = _id(_ref(book, "book"))
    d = await fetch(
        "/comment/list", {"lvc-page": page}, form={"Type": "Product", "EntityId": bid}, referer=url_for(f"/book/{bid}")
    )
    size = d.get("pageSize") or 20
    total = d.get("totalItems") or 0
    return {
        "book_id": bid,
        "total": total,
        "page": d.get("pageIndex") or page,
        "pages": -(-total // size),
        "comments": [_comment(c, max_chars) for c in d.get("items") or []],
    }


def _item(i: dict[str, Any]) -> dict[str, Any]:
    link = i.get("link") or ""
    m = re.match(r"/book/(\d+)", link)
    pts = re.search(r"pts=(\d+)", link)
    return {
        "book_id": int(m.group(1)) if m else i["id"],
        "edition_id": int(pts.group(1)) if pts else None,
        "title": i.get("name"),
        "title_en": i.get("englishName"),
        "author": i.get("fullName"),
        "price": i.get("priceOffer") or i.get("price"),
        "list_price": i.get("price") if i.get("discount") else None,
        "discount_pct": i.get("discount") or None,
        "note": i.get("shortDescription") or None,
    }


async def _list(
    kind: str, ident: int, sort: str, page: int, term: str | None, tags: list[str] | None = None
) -> dict[str, Any]:
    params: list[tuple[str, Any]] = [("sort", SORTS[sort]), ("page", page), ("term", term)]
    for t in tags or []:
        group, _, tag_id = t.partition("=")
        if not (group.isdigit() and tag_id.isdigit()):
            raise ToolError(f"Bad filter '{t}'. Use 'group=tag', both numbers, from ik_categories (e.g. '17=152').")
        params.append((f"tags-{group}", tag_id))
    d = await fetch(f"/{kind}/filter", dict(_multi(params)), form={"Id": ident})
    size = d.get("pageSize") or 24
    total = d.get("totalItems") or 0
    return {
        "total": total,
        "page": d.get("pageIndex") or page,
        "pages": -(-total // size),
        "books": [_item(i) for i in d.get("items") or []],
    }


def _multi(params: list[tuple[str, Any]]) -> dict[str, Any]:
    """Repeated keys (tags-17=a&tags-17=b) become a list value, which httpx sends as repeated params."""
    out: dict[str, Any] = {}
    for k, v in params:
        if k in out:
            out[k] = [*out[k], v] if isinstance(out[k], list) else [out[k], v]
        else:
            out[k] = v
    return out


SORT_FIELD = Annotated[
    Literal["newest", "bestselling", "most_liked"],
    Field(description="newest (default site order), bestselling, or most_liked."),
]
PAGE_FIELD = Annotated[
    int,
    Field(ge=1, le=500, description="Page number (24 books per page for categories and people, 18 for publishers)."),
]
TERM_FIELD = Annotated[str | None, Field(description="Optional words to search for inside this list.")]


@tool("Author or translator")
async def ik_profile(
    profile: Annotated[
        str,
        Field(
            description="Profile id from ik_search(kind='profile') or from a book's authors/translators, or an iranketab.ir/profile/ URL."
        ),
    ],
    sort: SORT_FIELD = "newest",
    page: PAGE_FIELD = 1,
    term: TERM_FIELD = None,
    bio_chars: Annotated[int, Field(ge=0, le=4000, description="Characters of the biography (0 = none).")] = 700,
) -> dict[str, Any]:
    """Read an author's or translator's profile (name, biography) and the books they wrote or translated.

    Profiles cover writers, translators and other contributors alike; the book list mixes everything they are
    credited on. Use it to see what else a translator has translated, then ik_book/ik_editions for one title.
    """
    path = _ref(profile, "profile")
    ident = _id(path)
    s = _soup(await fetch(path))
    name = s.select_one("h4.font-bold")
    if not name:
        raise ToolError(f"No profile with id {ident} on iranketab.ir.")
    bio = s.select_one("div.font-bold.text-default.text-justify")
    return {
        "profile_id": ident,
        "url": f"{SITE}/profile/{ident}",
        "name": _txt(name),
        "name_en": _txt(s.select_one("h5.font-en")) or None,
        "bio": _cut(_txt(bio), bio_chars) if bio and bio_chars else None,
        **await _list("profile", ident, sort, page, term),
    }


@tool("Publisher books")
async def ik_publisher_books(
    publisher: Annotated[
        str,
        Field(
            description="Publisher id from ik_search(kind='publisher') or from a book's edition, or an iranketab.ir/publisher/ URL."
        ),
    ],
    sort: SORT_FIELD = "bestselling",
    page: PAGE_FIELD = 1,
    term: TERM_FIELD = None,
) -> dict[str, Any]:
    """List the books of one publisher (انتشارات) on Iranketab, best sellers first by default.

    Use it to browse a publisher's catalogue or find its popular titles; then ik_book for one of them.
    """
    path = _ref(publisher, "publisher")
    ident = _id(path)
    s = _soup(await fetch(path))
    name = s.select_one("h4.font-bold")
    if not name:
        raise ToolError(f"No publisher with id {ident} on iranketab.ir.")
    return {
        "publisher_id": ident,
        "url": f"{SITE}/publisher/{ident}",
        "name": _txt(name),
        **await _list("brand", ident, sort, page, term),
    }


@tool("Browse a category")
async def ik_browse(
    category: Annotated[
        str,
        Field(
            description="Category (tag) id: 209 bestsellers, 207 newest books, 1 recommended, 103 fiction, 152 Russian literature... Full list via ik_categories."
        ),
    ],
    sort: SORT_FIELD = "newest",
    page: PAGE_FIELD = 1,
    term: TERM_FIELD = None,
    filters: Annotated[
        list[str] | None,
        Field(
            description="Narrow by sub-categories as 'group=tag' strings from ik_categories(category), e.g. ['17=152'] for Russian literature. Different groups are combined with AND."
        ),
    ] = None,
) -> dict[str, Any]:
    """List books of a category, bestseller list or award list, with sort, in-list search and sub-category filters.

    Bestsellers are category 209, the newest books 207, the staff picks 1, the 30% weekly discount festival 325,
    signed copies 1293. Prices are in Toman. Prize winners and series are categories too (ik_lists); filters can
    narrow a list, e.g. discounted prize winners. `term` searches titles inside the list and can be slow on huge
    lists such as 103. Use ik_categories for other ids and filter groups; then ik_book for a title.
    """
    path = _ref(category, "tag")
    return {"category_id": _id(path), **await _list("tag", _id(path), sort, page, term, filters)}


@tool("Categories and filters")
async def ik_categories(
    category: Annotated[
        str | None, Field(description="Category id to see its filter groups; omit for the main menu categories.")
    ] = None,
    group: Annotated[
        int | None, Field(description="With a category: list every option of this filter group id.")
    ] = None,
) -> dict[str, Any]:
    """List Iranketab's menu categories, or the sub-category filter groups of one category.

    Without arguments it returns the main menu (id and name), including bestseller and award lists. With a category id
    it returns the filter groups usable in ik_browse (group id, label, a few options as tag id: name); pass `group` to
    list one group completely.
    """
    if category is None:
        s = _soup(await fetch("/"))
        menu: dict[int, str] = {}
        for a in s.select('a[href*="/tag/"]'):
            if m := re.search(r"/tag/(\d+)-([^?#]*)", a["href"]):
                label = _txt(a)  # "view all" links carry no name: fall back to the url slug
                menu.setdefault(
                    int(m.group(1)), label if label not in ("", "مشاهده همه") else m.group(2).replace("-", " ")
                )
        return {"count": len(menu), "categories": [{"id": k, "name": v} for k, v in menu.items()]}
    path = _ref(category, "tag")
    s = _soup(await fetch(path))
    groups = []
    for sel in s.select('select[name^="tag_"]'):
        gid = int(sel["name"][4:])
        opts = [(o["value"], _txt(o)) for o in sel.find_all("option")]
        if group is not None and gid != group:
            continue
        label = sel.find_previous("label")
        groups.append(
            {
                "group": gid,
                "label": _txt(label),
                "options_count": len(opts),
                "options": {k: v for k, v in (opts if group is not None else opts[:12])},
            }
        )
    return {
        "category_id": _id(path),
        "name": (s.title.string or "").split("|")[0].strip() if s.title else None,
        "filter_groups": groups,
        "usage": "ik_browse(category, filters=['<group>=<tag id>'])",
    }
