"""Utility functions."""

from datetime import datetime
import re


def parse_pubdate(pubdate_str):
    """Convert a pubdate string to ISO format for calibre.

    Returns ISO format string or None if parsing fails.
    """
    if not pubdate_str:
        return None

    pubdate_str = pubdate_str.strip()

    # Try various formats
    formats = [
        "%Y-%m-%d",
        "%Y-%m",
        "%Y年%m月%d日",
        "%Y年%m月",
        "%Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(pubdate_str, fmt)
            if "%m" in fmt:
                return dt.strftime("%Y-%m-%d 00:00:00+00:00")
            return dt.strftime("%Y-01-01 00:00:00+00:00")
        except ValueError:
            continue

    # Fallback: extract year with regex
    m = re.search(r"(\d{4})", pubdate_str)
    if m:
        return f"{m.group(1)}-01-01 00:00:00+00:00"

    return None


def clean_title(title):
    """Extract core title, removing marketing noise."""
    t = title.split("（")[0].split("(")[0].strip()
    for sep in ["_", "—", "–"]:
        if sep in t:
            t = t.split(sep)[0].strip()
    return t


def clean_author(author):
    """Extract core author name."""
    a = author.strip()
    for pat in [r"著[；;]", r"译[；;]", r"编著[；;]", r"编[；;]", r"，.*译", r"\s+译$"]:
        a = re.sub(pat, "", a)
    a = re.sub(r"^[\[【（(]\s*", "", a)
    a = re.sub(r"\s*[\]】）)]\s*$", "", a)
    return a.strip()


def title_matches(query_title, db_title):
    """Check if a search result title matches the database title."""
    ct = clean_title(query_title)
    dt = clean_title(db_title)
    return ct == dt or ct in dt or dt in ct
