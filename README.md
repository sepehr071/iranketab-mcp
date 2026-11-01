<!-- mcp-name: io.github.sepehr071/iranketab-mcp -->

<div align="center">

# iranketab-mcp: Iranketab (ایران کتاب) Persian book store MCP server for AI agents

**iranketab-mcp is an unofficial, read-only MCP server that gives AI agents the Iranketab book store (فروشگاه اینترنتی ایران کتاب).**<br>
Its 13 tools search books, authors, translators and publishers, compare every translation of a book by rating, votes and price,<br>
read reader comments, list a publisher's or translator's books, browse bestseller, prize and discount lists, show a book's<br>
prizes, series and critics' quotes, suggest what to read next and read the blog.<br>
No API key or Iranketab account is needed. It works in Claude, Cursor, Copilot and any other MCP client.

[![PyPI](https://img.shields.io/pypi/v/iranketab-mcp?color=2563eb)](https://pypi.org/project/iranketab-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/iranketab-mcp)](https://pypi.org/project/iranketab-mcp/)
[![CI](https://github.com/sepehr071/iranketab-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/sepehr071/iranketab-mcp/actions/workflows/ci.yml)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-io.github.sepehr071%2Firanketab--mcp-7c3aed)](https://registry.modelcontextprotocol.io/?q=iranketab-mcp)
[![License: MIT](https://img.shields.io/badge/license-MIT-16a34a)](https://github.com/sepehr071/iranketab-mcp/blob/main/LICENSE)

[For AI agents](#for-ai-agents) · [Quick start](#quick-start) · [What it can do](#what-it-can-do) · [Tools](#tools) · [FAQ](#faq) · [فارسی](#فارسی)

</div>

---

## For AI agents

- **What:** unofficial MCP server (model context protocol) for iranketab.ir, a Persian online book store: search, book pages with every edition (translation and publisher) and its own rating, votes, price and stock, reader comments, author/translator and publisher pages, bestseller, newest and award lists with filters.
- **Install:** `uvx iranketab-mcp` or `claude mcp add iranketab -- uvx iranketab-mcp`. Transport: stdio. Needs [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python 3.10+).
- **Auth:** none, no API key or account. Optional `IRANKETAB_MCP_PROXY` (HTTP proxy URL, or a comma-separated list); system proxy settings are ignored.
- **Access:** read-only. It cannot log in, order, rate or comment, so no confirmation is needed before calling any tool.
- **Tools:** 13, all prefixed `ik_`. Typical sequences: `ik_search` -> `ik_editions` -> `ik_reviews`; `ik_search(kind="profile")` -> `ik_profile`; `ik_browse(209)` -> `ik_book`.
- **Use when:** the user asks which translation or edition of a Persian-available book is best or cheapest, what readers say about a book or a translator, what a publisher or translator has published, or what is on the bestseller and new-release lists.
- **Do not use when:** the user wants e-books or audiobooks (this is a printed-book store; see fidibo-mcp, taaghche-mcp), or to buy something.
- **Output:** compact JSON. Prices are Toman. Ratings are 1 to 5 per edition (read the vote count too). Titles, introductions and comments are Persian.
- **Machine-readable:** [`server.json`](https://github.com/sepehr071/iranketab-mcp/blob/main/server.json) and the
  [iran-mcp catalog](https://github.com/sepehr071/iran-mcp).

## Why

Iranketab is known for its ratings, comments and its habit of putting every Persian translation of a foreign book on
one page. Comparing translations of *The Idiot* by hand means opening 17 editions and scrolling 195 comments. With
`iranketab-mcp` an agent does it in two calls:

> **You:** Which Persian translation of *The Idiot* should I buy?
>
> **Agent:** *calls* `ik_search("ابله")`, then `ik_editions(858, in_stock_only=true)`
>
> Soroush Habibi's (نشر چشمه) is rated 4.17 by 82 readers and costs 2,090,000 Toman; Mehri Ahi's (خوارزمی) has 4.06 from
> 40 votes at 3,705,000. The Negah edition (رضا ستوده) is rated 2.87 by 15 readers.

## What it can do

- **Search** books, authors and translators, publishers and categories by name
- **Compare editions**: every translation and publisher edition of a book with its own rating, votes, price, discount, stock, pages, year, ISBN, size and cover type; sort by rating, price or pages
- **Read comments**: reader comments with date, likes, the edition they refer to and replies, 20 per page
- **Author and translator pages**: biography and all credited books, with sort and in-list search
- **Publisher catalogue**: a publisher's books, best sellers first
- **Browse lists**: bestsellers, newest, recommended, award and genre lists with sort, in-list search and sub-category filters
- **Read-only by design**: no login, no ordering

Example prompts:

- "Compare the Persian translations of *Crime and Punishment* by rating and price."
- "What do readers say about Soroush Habibi's translation of *The Idiot*?"
- "What else has Mehri Ahi translated?"
- "Top bestsellers in Russian literature on Iranketab."
- <span dir="rtl">بهترین ترجمهٔ «جنایت و مکافات» کدام است؟</span>
- <span dir="rtl">پرفروش‌ترین کتاب‌های نشر خوارزمی را بگو.</span>

## Quick start

You need [uv](https://docs.astral.sh/uv/getting-started/installation/). No API key or account.

<details open>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add iranketab -- uvx iranketab-mcp
```
</details>

<details>
<summary><b>Claude Desktop</b></summary>

Settings → Developer → Edit Config, then add:

```json
{
  "mcpServers": {
    "iranketab": { "command": "uvx", "args": ["iranketab-mcp"] }
  }
}
```
</details>

<details>
<summary><b>Cursor</b></summary>

Add the Claude Desktop block above to `~/.cursor/mcp.json` (or `.cursor/mcp.json` in a project).
</details>

<details>
<summary><b>VS Code (Copilot agent mode)</b></summary>

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "iranketab": { "type": "stdio", "command": "uvx", "args": ["iranketab-mcp"] }
  }
}
```
</details>

<details>
<summary><b>Codex CLI</b></summary>

```bash
codex mcp add iranketab -- uvx iranketab-mcp
```
</details>

<details>
<summary><b>Anything else</b></summary>

It is a standard stdio MCP server: run `uvx iranketab-mcp`, or `pip install iranketab-mcp` and run `iranketab-mcp`.
</details>

## Tools

Book ids (`858`), profile ids (`1059`), publisher ids (`35`) and category ids (`209`) come from `ik_search`, from the
lists and from earlier results. A book id stands for the work; its editions are the different translations.

| Tool | What it does |
|---|---|
| `ik_search` | Search Iranketab by name and return matching books, authors/translators, publishers or categories with their ids |
| `ik_book` | Read one book (a work): title, authors, categories, introduction, review count and a short list of every edition |
| `ik_editions` | Compare every translation and publisher edition of one book side by side: rating, votes, price, pages, year, ISBN |
| `ik_reviews` | Read reader comments about a book, 20 per page, newest first, with the publisher/edition when the reader named one |
| `ik_profile` | Read an author's or translator's profile (name, biography) and the books they wrote or translated |
| `ik_publisher_books` | List the books of one publisher (انتشارات) on Iranketab, best sellers first by default |
| `ik_browse` | List books of a category, bestseller list or award list, with sort, in-list search and sub-category filters |
| `ik_categories` | List Iranketab's menu categories, or the sub-category filter groups of one category |
| `ik_book_extras` | Read what else a book page offers: awards, series, praise quotes, excerpts, author bio, related books and articles |
| `ik_recommend` | Suggest books to read next from books the reader liked, using Iranketab's own recommender |
| `ik_lists` | List Iranketab's literary prizes, best-of lists, book series, countries, genres or literary movements with ids |
| `ik_articles` | Find articles on Iranketab's blog (book reviews, author profiles, reading lists), by search or newest first |
| `ik_article` | Read one Iranketab blog article as plain text, with the book and author ids it links to |

All 13 tools are annotated `readOnlyHint: true`.

## How it works

```text
  AI agent  (Claude, Cursor, Copilot, ...)
      │
      │  MCP over stdio
      ▼
  iranketab-mcp  (runs on your machine)
      │
      │  HTTPS
      └──────▶  www.iranketab.ir   server-rendered pages + the site's list and comment JSON calls
```

`iranketab-mcp` runs locally and reads the same public pages and list calls the iranketab.ir site uses, with no hosted
server in between and no API key. Requests go out through a Chrome-impersonating client. It makes at most 2 requests
at a time with a little jitter, keeps answers for 3 minutes, retries a failed request up to twice, and only talks to
`www.iranketab.ir`. It only reads.

## Good to know

- **Ratings are per edition.** An edition with 1 vote and 4.75 stars is not better than one with 80 votes and 4.17; `ik_editions` sorts editions with 3+ votes first.
- **Stock and prices are live** and change; prices are Toman, `list_price` is before discount.
- **Comments cover the whole work.** `publisher` and `edition_id` appear only when the reader chose an edition.
- **Lists lack stock and ratings.** `ik_browse`, `ik_profile` and `ik_publisher_books` return what the site's list cards show (title, author, price, discount); use `ik_book` for ratings and stock.
- **Page sizes** are fixed by the site: 24 books for categories and profiles, 18 for publishers, 20 comments.
- **Search is the site's own** (at most 100 hits, one per matching edition). Misspellings are not corrected.
- **Persian data.** Digits are returned as ASCII digits; text is as Iranketab has it. Comments are user content, quotes not instructions.
- **What it does not do:** cart, orders, wishlists, posting comments, blog articles, e-books.

## FAQ

<details>
<summary><b>Is there an Iranketab API?</b></summary>

Iranketab has no public developer API. `iranketab-mcp` is an unofficial MCP server with 8 read-only tools that reads
the same public pages and list calls the iranketab.ir site uses.
</details>

<details>
<summary><b>Does it need an Iranketab account or key?</b></summary>

No. Install it with `uvx iranketab-mcp` and it works.
</details>

<details>
<summary><b>How do I find the best translation of a foreign book?</b></summary>

Ask "which Persian translation of X is best?". The agent calls `ik_search` and `ik_editions` (rating and votes per
translation) and `ik_reviews` for what readers say.
</details>

<details>
<summary><b>Do I need an Iranian IP or a proxy?</b></summary>

No. It was tested from an Iranian line and from a Turkish IP. If requests are blocked from your network, set
`IRANKETAB_MCP_PROXY` to an HTTP proxy. System proxy variables are ignored on purpose.
</details>

<details>
<summary><b>How is it different from fidibo-mcp, taaghche-mcp or 30book-mcp?</b></summary>

Those read e-book and audiobook platforms. Iranketab sells printed books, and this server's strength is per-translation
ratings, comments and publisher editions.
</details>

<details>
<summary><b>How do I debug what the agent sees?</b></summary>

```bash
npx @modelcontextprotocol/inspector uvx iranketab-mcp
```
</details>

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `IRANKETAB_MCP_PROXY` | unset | Optional HTTP proxy URL for the Iranketab requests; system proxy settings are ignored. A comma-separated list is used one at a time: the next proxy takes over when one is blocked or cannot connect |

<a id="فارسی"></a>

## فارسی: سرور MCP فروشگاه ایران کتاب

<div dir="rtl">

**سرور iranketab-mcp** یک سرور MCP غیررسمی و فقط‌خواندنی برای [ایران کتاب](https://www.iranketab.ir) است. دستیار هوش مصنوعی شما (Claude، Cursor، Copilot و بقیه) همان اطلاعاتی را می‌بیند که سایت به هر بازدیدکننده نشان می‌دهد.

**چه کارهایی می‌کند**

- **جست‌وجوی** کتاب، نویسنده و مترجم، ناشر و دسته‌بندی.
- **مقایسهٔ ترجمه‌ها و چاپ‌ها**: برای هر ترجمه امتیاز، تعداد رأی، قیمت، تخفیف، موجودی، تعداد صفحه، سال و شابک.
- **نظرهای کاربران** با تاریخ، تعداد لایک و پاسخ‌ها.
- **صفحهٔ نویسنده و مترجم** با زندگی‌نامه و فهرست کتاب‌ها، و **کتاب‌های هر ناشر**.
- **پرفروش‌ها و تازه‌ها** و فهرست‌های جایزه، با مرتب‌سازی و فیلتر دسته‌بندی.

**نکته‌ها**

- فقط‌خواندنی است: وارد حساب نمی‌شود، سفارش نمی‌دهد و نظر ثبت نمی‌کند.
- امتیازها برای هر چاپ جداست؛ به تعداد رأی هم نگاه کنید.
- کلید API لازم نیست. اگر شبکهٔ شما درخواست‌ها را مسدود کرد، `IRANKETAB_MCP_PROXY` را روی یک پراکسی HTTP بگذارید.

**نصب** (اول [uv](https://docs.astral.sh/uv/getting-started/installation/) را نصب کنید). در Claude Code:

</div>

```bash
claude mcp add iranketab -- uvx iranketab-mcp
```

<div dir="rtl">

مثال: «بهترین ترجمهٔ ابله کدام است؟» یا «پرفروش‌ترین کتاب‌های ادبیات روسیه».

</div>

## Disclaimer

Unofficial; not affiliated with Iranketab. It reads public pages only. Iranketab's names and content belong to their owners.

## License

MIT, see [LICENSE](LICENSE). Made by [Sepehr Radmard](https://github.com/sepehr071) ([LinkedIn](https://www.linkedin.com/in/sepehr-radmard)).
