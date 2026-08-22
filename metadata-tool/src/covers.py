"""Cover download functionality."""

import os
import requests


class CoverDownloader:
    """Download book covers from various sources."""

    def __init__(self, proxy=None, timeout=20, user_agent=None, min_size=2000):
        self.timeout = timeout
        self.min_size = min_size
        self.session = requests.Session()
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
        self.session.headers.update({
            "User-Agent": user_agent or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://book.douban.com/",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        })

    def download(self, url, save_path):
        """Download an image from URL to save_path.

        Returns (success: bool, size: int).
        """
        try:
            r = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            if r.status_code == 200 and len(r.content) > self.min_size:
                # Verify it's an image
                content_type = r.headers.get("content-type", "")
                if "image" in content_type or url.endswith(".jpg") or url.endswith(".png"):
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    with open(save_path, "wb") as f:
                        f.write(r.content)
                    return True, len(r.content)
        except Exception as e:
            print(f"  [Cover] Download error: {e}")
        return False, 0

    def download_douban_cover(self, douban_id, save_path):
        """Download cover from Douban using the image ID."""
        # Try different image server prefixes
        for prefix in ["img1", "img2", "img9"]:
            for size in ["/l/", "/m/", "/s/"]:
                url = f"https://{prefix}.doubanio.com/view/subject{size}public/s{douban_id}.jpg"
                ok, size_bytes = self.download(url, save_path)
                if ok:
                    return True, size_bytes
        return False, 0

    def download_openlibrary_cover(self, cover_url, save_path):
        """Download cover from Open Library."""
        if cover_url:
            return self.download(cover_url, save_path)
        return False, 0
