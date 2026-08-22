"""Douban Books API client."""

import re
import time
import requests


class DoubanAPI:
    """Douban Books API client."""

    def __init__(self, proxy=None, timeout=15, user_agent=None, delay=1.5):
        self.proxy = proxy
        self.timeout = timeout
        self.delay = delay
        self.session = requests.Session()
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
        self.session.headers.update({
            "User-Agent": user_agent or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://book.douban.com/",
        })
        self._last_call = 0

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_call
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_call = time.time()

    def search(self, query, limit=5):
        """Search for books on Douban."""
        self._rate_limit()
        try:
            r = self.session.get(
                "https://book.douban.com/j/subject_suggest",
                params={"q": query},
                timeout=self.timeout,
            )
            if r.status_code == 200:
                return r.json()[:limit]
        except Exception as e:
            print(f"  [Douban] Search error: {e}")
        return []

    def get_detail(self, douban_id):
        """Get detailed metadata from a Douban book page."""
        self._rate_limit()
        try:
            r = self.session.get(
                f"https://book.douban.com/subject/{douban_id}/",
                timeout=self.timeout,
            )
            if r.status_code != 200:
                return {}
            return self._parse_detail_page(r.text)
        except Exception as e:
            print(f"  [Douban] Detail error: {e}")
        return {}

    def _parse_detail_page(self, html):
        """Parse Douban book detail page HTML."""
        result = {}

        # Parse meta tags
        for prop, content in re.findall(
            r'<meta\s+property="([^"]+)"\s+content="([^"]*?)"', html
        ):
            if prop == "book:isbn":
                result["isbn"] = content
            elif prop == "og:description":
                result["description"] = content
            elif prop == "og:image":
                result["cover_url"] = content

        # Parse info list
        patterns = {
            "pubdate": r'<span class="pl">出版年:</span>\s*([^<]+)',
            "publisher": r'<span class="pl">出版社:</span>\s*([^<]+)',
            "pages": r'<span class="pl">页数:</span>\s*([^<]+)',
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, html)
            if match:
                result[key] = match.group(1).strip()

        # Parse tags
        tags = re.findall(r'<a[^>]*class="tag"[^>]*>([^<]+)</a>', html)
        if tags:
            result["tags"] = tags[:5]

        return result

    def find_book(self, title, author=""):
        """Search and return the best matching book with details."""
        core_title = self._clean_title(title)
        results = self.search(core_title)

        if not results and author:
            results = self.search(author)

        if not results:
            return None

        # Try to match by title
        clean_a = self._clean_author(author) if author else ""
        best = None
        for item in results:
            item_title = item.get("title", "")
            item_author = item.get("author_name", "")

            # Exact match
            if core_title == item_title or item_title == title:
                best = item
                break

            # Partial match + author match
            if core_title in item_title or item_title in core_title:
                if clean_a and clean_a in item_author:
                    best = item
                    break
                if not best:
                    best = item

        if not best:
            best = results[0]

        # Get detailed metadata
        detail = self.get_detail(best.get("id"))
        detail["douban_id"] = best.get("id")
        detail["douban_title"] = best.get("title")
        return detail

    @staticmethod
    def _clean_title(title):
        """Extract core title."""
        t = title.split("（")[0].split("(")[0].strip()
        for sep in ["_", "—", "–"]:
            if sep in t:
                t = t.split(sep)[0].strip()
        return t

    @staticmethod
    def _clean_author(author):
        """Extract core author name."""
        a = author.strip()
        for pat in [r"著[；;]", r"译[；;]", r"编著[；;]", r"编[；;]", r"，.*译", r"\s+译$"]:
            a = re.sub(pat, "", a)
        a = re.sub(r"^[\[【（(]\s*", "", a)
        a = re.sub(r"\s*[\]】）)]\s*$", "", a)
        return a.strip()
