from urllib.parse import quote_plus, unquote
import urllib.parse as up
import textwrap
import asyncio
import base64
import json
import re


from bs4 import BeautifulSoup
import aiohttp

from tools.kit import tool


UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
HEADERS = {"User-Agent": UA}
BROWSER_HEADERS = {
    **HEADERS,
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://duckduckgo.com/",
    "Connection": "keep-alive",
}

DDG = "https://duckduckgo.com/html/?q={q}&num={n}&kl=us-en"
STACKPRINTER = (
    "https://stackoverflow.stackprinter.appspot.com/questions/{qid}"
    "?service=stackoverflow&language=en&hideAnswers=false&expandSnippets=true&width=640"
)


async def fetch(log, session, url, retry: True, *, as_json=False):
    url = "http:" + url if url.startswith("//") else url
    log.debug("GET url[%s]", url)
    async with session.get(url, headers=HEADERS, timeout=30) as r:
        if r.status in (401, 403) and retry:
            async with session.get(url, headers=BROWSER_HEADERS, timeout=30) as r2:
                r2.raise_for_status()
                return await (r2.json() if as_json else r2.text())
        r.raise_for_status()
        return await (r.json() if as_json else r.text())


###############################################################################
# DUCKDUCKGO SEARCH → [(title, url, serp_snippet)]
###############################################################################
def _shorten(s, n=800):
    return textwrap.shorten(s.replace("\n", " "), n, placeholder="…")


async def ddg_search(log, query, k, debug):
    async with aiohttp.ClientSession() as s:
        html = await fetch(log, s, DDG.format(q=quote_plus(query), n=k), retry=True)
    if debug:
        log.debug("got DDG_RAW[%s]", _shorten(html))

    soup = BeautifulSoup(html, "html.parser")
    hits = []
    for res in soup.select("div.result")[:k]:
        a, sn = res.select_one("a.result__a"), res.select_one("a.result__snippet")
        if not a:
            continue
        href = a["href"]
        if "/l/?" in href:  # strip DDG redirect wrapper
            href = unquote(up.parse_qs(up.urlparse(href).query)["uddg"][0])
        hits.append(
            (
                a.get_text(" ", strip=True),
                href,
                sn.get_text(" ", strip=True) if sn else "",
            )
        )
    log.debug("ddg extracted n_links[%s]", len(hits))
    return hits


###############################################################################
# SPECIAL-CASE HANDLERS
###############################################################################
SO_ID = re.compile(r"/questions/(\d+)")
GH_BLOB = re.compile(r"https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)")
GH_ROOT = re.compile(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")


async def so_extract(session, url):
    m = SO_ID.search(url)
    if not m:
        return ""
    html = await fetch(session, STACKPRINTER.format(qid=m.group(1)), retry=False)
    soup = BeautifulSoup(html, "html.parser")
    q = soup.select_one(".question .post-text")
    a = soup.select_one(".answer.accepted-answer .post-text") or soup.select_one(
        ".answer .post-text"
    )
    return (
        f"Q: {q.get_text(' ', strip=True) if q else ''}  "
        f"A: {a.get_text(' ', strip=True) if a else ''}"
    )


async def gh_extract(session, url):
    # raw blob
    m = GH_BLOB.match(url)
    if m:
        owner, repo, branch, path = m.groups()
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        return await fetch(session, raw_url, retry=False)

    # repo root → README via API
    m = GH_ROOT.match(url)
    if m:
        owner, repo = m.groups()
        api = f"https://api.github.com/repos/{owner}/{repo}/readme"
        j = await fetch(session, api, retry=False, as_json=True)
        content = base64.b64decode(j["content"]).decode("utf-8", errors="ignore")
        return content
    return ""


async def reddit_extract(session, url):
    # JSON endpoint returns list[ post, comments ]
    json_url = url.rstrip("/") + ".json?limit=20&raw_json=1"
    data = await fetch(session, json_url, retry=False, as_json=True)
    if not isinstance(data, list) or len(data) < 2:
        return ""
    post = data[0]["data"]["children"][0]["data"]
    comments = data[1]["data"]["children"]
    top_comment = max(
        (c for c in comments if c["kind"] == "t1"),
        key=lambda c: c["data"].get("score", 0),
        default=None,
    )
    post_txt = post.get("selftext") or post.get("title", "")
    top_txt = top_comment["data"]["body"] if top_comment else ""
    return f"Post: {post_txt}  TopComment: {top_txt}"


###############################################################################
# SCRAPE ROUTER
###############################################################################
async def scrape(log, session, url, fallback, max_paras=4):
    try:
        dom = up.urlparse(url).netloc.lower()

        if "stackoverflow.com" in dom:
            return await so_extract(session, url) or fallback

        if "github.com" in dom:
            txt = await gh_extract(session, url)
            return txt if txt else fallback

        if "reddit.com" in dom:
            txt = await reddit_extract(session, url)
            return txt if txt else fallback

        # generic HTML
        html = await fetch(log, session, url, retry=True)
        paras = [
            p.get_text(" ", strip=True)
            for p in BeautifulSoup(html, "html.parser").select("p")[:max_paras]
        ]
        return " ".join(paras) or fallback

    except Exception as e:
        log.warning("Giving up on url[%s]: got error[%s]", url, e)
        return fallback


###############################################################################
# PUBLIC TOOL
###############################################################################
@tool(
    "Search DuckDuckGo with the given query and return the top k results",
    query="the query to search",
    k="number of results to include, default is 5",
)
async def web_search(query: str, k: int = 5, debug=False):
    log = web_search.ref.log
    links = await ddg_search(log, query, k, debug)
    async with aiohttp.ClientSession() as sess:
        bodies = await asyncio.gather(
            *[scrape(log, sess, u, fallback=snip) for _, u, snip in links],
            return_exceptions=True,
        )
    out = [
        {"title": t, "url": u, "snippet": b if isinstance(b, str) else ""}
        for (t, u, _), b in zip(links, bodies)
    ]
    if debug:
        import sys

        json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
        print()
    return out
