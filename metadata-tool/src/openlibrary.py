"""Open Library API client."""

import re
import time
import requests


class OpenLibraryAPI:
    """Open Library API client."""

    def __init__(self, proxy=None, timeout=15, user_agent=None, delay=1.5):
        self.proxy = proxy
        self.timeout = timeout
        self.delay = delay
        self.session = requests.Session()
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
        self.session.headers.update({
            "User-Agent": user_agent or "Mozilla/5.0",
        })
        self._last_call = 0

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_call
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_call = time.time()

    def search(self, query, limit=3):
        """Search for books on Open Library."""
        self._rate_limit()
        try:
            r = self.session.get(
                "https://openlibrary.org/search.json",
                params={"q": query, "limit": limit},
                timeout=self.timeout,
            )
            if r.status_code == 200:
                return r.json().get("docs", [])[:limit]
        except Exception as e:
            print(f"  [OpenLibrary] Search error: {e}")
        return []

    def get_cover_url(self, cover_i=None, isbn=None):
        """Get cover image URL from Open Library."""
        if cover_i:
            return f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg"
        if isbn:
            return f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
        return None

    def find_book(self, title, author=""):
        """Search and return the best matching book."""
        results = self.search(title)
        if not results and author:
            results = self.search(author)

        if not results:
            return None

        # Return the first match
        doc = results[0]
        return {
            "title": doc.get("title", ""),
            "authors": doc.get("author_name", []),
            "first_publish_year": doc.get("first_publish_year"),
            "isbn": doc.get("isbn", []),
            "cover_i": doc.get("cover_i"),
            "cover_url": self.get_cover_url(cover_i=doc.get("cover_i")),
        }
