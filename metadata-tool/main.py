#!/usr/bin/env python3
"""
Calibre Metadata Manager
========================
Automatically fills missing metadata for books in a calibre library.
Sources: Douban Books, Open Library.

Usage:
    python main.py                    # Fill all missing metadata
    python main.py --check            # Check what's missing (dry run)
    python main.py --book-id 12       # Process a specific book
    python main.py --covers-only      # Only download missing covers
    python main.py --report           # Generate a report
"""

import argparse
import os
import sys
import yaml

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db import CalibreDB
from src.douban import DoubanAPI
from src.openlibrary import OpenLibraryAPI
from src.covers import CoverDownloader
from src.utils import parse_pubdate


def load_config(config_path=None):
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def fill_book_metadata(book, db, douban, openlibrary, cover_downloader, config):
    """Fill missing metadata for a single book.

    Returns dict of what was updated.
    """
    book_id = book["id"]
    title = book["title"]
    authors = book.get("authors", "")
    author = authors.split(",")[0] if authors else ""

    updates = {}
    missing = db.get_missing_fields(book)

    if not missing:
        return updates

    print(f"\n[{book_id}] {title[:50]}... | {author[:30]}")

    # Search Douban first
    douban_data = None
    if config["sources"][0]["name"] == "douban" and douban:
        douban_data = douban.find_book(title, author)

    # Search Open Library as fallback
    openlibrary_data = None
    if not douban_data and openlibrary:
        openlibrary_data = openlibrary.find_book(title, author)

    # Use whichever source returned data
    source_data = douban_data or openlibrary_data
    if not source_data:
        print("  -> Not found in any source")
        return updates

    source_name = "Douban" if douban_data else "Open Library"
    print(f"  -> Found via {source_name}: {source_data.get('title', source_data.get('douban_title', '?'))}")

    # Fill ISBN
    if "isbn" in missing and source_data.get("isbn"):
        isbn = source_data["isbn"]
        if isinstance(isbn, list):
            isbn = isbn[0] if isbn else ""
        if isbn:
            updates["isbn"] = isbn
            print(f"  + isbn: {isbn}")

    # Fill pubdate
    if "pubdate" in missing and source_data.get("pubdate"):
        pd = parse_pubdate(source_data["pubdate"])
        if pd:
            updates["pubdate"] = pd
            print(f"  + pubdate: {source_data['pubdate']}")

    # Fill description
    if "description" in missing and source_data.get("description"):
        db.add_description(book_id, source_data["description"])
        print(f"  + description ({len(source_data['description'])} chars)")

    # Fill tags
    if "tags" in missing and source_data.get("tags"):
        existing_tags = db.get_existing_tags(book_id)
        for tag in source_data["tags"]:
            if tag not in existing_tags:
                db.add_tag(book_id, tag)
                print(f"  + tag: {tag}")

    # Download cover
    if "cover" in missing and cover_downloader:
        book_dir = db.get_book_path(book_path=book)
        cover_path = os.path.join(book_dir, "cover.jpg")

        if not os.path.exists(cover_path):
            downloaded = False

            # Try Douban cover
            if douban_data and douban_data.get("douban_id"):
                print(f"  Downloading cover from Douban...")
                ok, size = cover_downloader.download_douban_cover(
                    douban_data["douban_id"], cover_path
                )
                if ok:
                    print(f"  + cover ({size} bytes)")
                    downloaded = True
                    updates["has_cover"] = 1

            # Try Open Library cover
            if not downloaded and openlibrary_data and openlibrary_data.get("cover_url"):
                print(f"  Downloading cover from Open Library...")
                ok, size = cover_downloader.download_openlibrary_cover(
                    openlibrary_data["cover_url"], cover_path
                )
                if ok:
                    print(f"  + cover ({size} bytes)")
                    downloaded = True
                    updates["has_cover"] = 1

            if not downloaded:
                print(f"  - cover not available")

    # Apply book-level updates
    if updates:
        db.update_book(book_id, updates)

    return updates


def check_missing(db):
    """Check and report what metadata is missing across all books."""
    books = db.get_all_books()
    stats = {"total": len(books), "missing_isbn": 0, "missing_pubdate": 0,
             "missing_desc": 0, "missing_cover": 0, "complete": 0}

    print(f"\n{'='*60}")
    print(f"Library: {len(books)} books")
    print(f"{'='*60}")

    for book in books:
        missing = db.get_missing_fields(book)
        if not missing:
            stats["complete"] += 1
            continue

        if "isbn" in missing:
            stats["missing_isbn"] += 1
        if "pubdate" in missing:
            stats["missing_pubdate"] += 1
        if "description" in missing:
            stats["missing_desc"] += 1
        if "cover" in missing:
            stats["missing_cover"] += 1

        print(f"  [{book['id']}] {book['title'][:45]}... | missing: {', '.join(missing)}")

    print(f"\n{'='*60}")
    print(f"Complete: {stats['complete']}/{stats['total']}")
    print(f"Missing ISBN: {stats['missing_isbn']}")
    print(f"Missing pubdate: {stats['missing_pubdate']}")
    print(f"Missing description: {stats['missing_desc']}")
    print(f"Missing cover: {stats['missing_cover']}")
    print(f"{'='*60}")

    return stats


def generate_report(db):
    """Generate a detailed report of all books."""
    books = db.get_all_books()

    print(f"\n{'='*80}")
    print(f"{'ID':>4} | {'Title':<45} | {'ISBN':<14} | {'Pub':<4} | {'Desc':<4} | {'Cover':<5}")
    print(f"{'-'*80}")

    for book in books:
        has_isbn = "Y" if book.get("isbn") else "N"
        has_pub = "Y" if book.get("pubdate", "9999") >= "1900-01-01" else "N"
        has_desc = "Y" if db.has_description(book["id"]) else "N"
        has_cover = "Y" if book.get("has_cover") else "N"

        print(f"{book['id']:>4} | {book['title'][:45]:<45} | {book.get('isbn', '')[:13]:<14} | {has_pub:<4} | {has_desc:<4} | {has_cover:<5}")

    print(f"{'='*80}")


def main():
    parser = argparse.ArgumentParser(description="Calibre Metadata Manager")
    parser.add_argument("--config", help="Path to config.yaml")
    parser.add_argument("--check", action="store_true", help="Check missing metadata (dry run)")
    parser.add_argument("--report", action="store_true", help="Generate detailed report")
    parser.add_argument("--book-id", type=int, help="Process a specific book by ID")
    parser.add_argument("--covers-only", action="store_true", help="Only download missing covers")
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Initialize components
    db = CalibreDB(config["library"]["db_path"])
    network = config["network"]

    douban = DoubanAPI(
        proxy=network["proxy"],
        timeout=network["timeout"],
        user_agent=network["user_agent"],
        delay=network["rate_limit_delay"],
    ) if config["sources"][0]["enabled"] else None

    openlibrary = OpenLibraryAPI(
        proxy=network["proxy"],
        timeout=network["timeout"],
        user_agent=network["user_agent"],
    ) if len(config["sources"]) > 1 and config["sources"][1]["enabled"] else None

    cover_downloader = CoverDownloader(
        proxy=network["proxy"],
        timeout=network["timeout"],
        user_agent=network["user_agent"],
        min_size=config["cover"]["min_size"],
    ) if config["fields"]["cover"] else None

    # Check mode
    if args.check:
        check_missing(db)
        return

    # Report mode
    if args.report:
        generate_report(db)
        return

    # Process books
    if args.book_id:
        book = db.get_book_by_id(args.book_id)
        if not book:
            print(f"Book {args.book_id} not found")
            return
        books = [book]
    else:
        books = db.get_all_books()

    total_updates = 0
    for book in books:
        if args.covers_only:
            # Only process books missing covers
            if book.get("has_cover"):
                continue
            missing = ["cover"]
        else:
            missing = db.get_missing_fields(book)
            if not missing:
                continue

        updates = fill_book_metadata(book, db, douban, openlibrary, cover_downloader, config)
        total_updates += len(updates)

    print(f"\n{'='*50}")
    print(f"Done! Updated {total_updates} fields across {len(books)} books.")


if __name__ == "__main__":
    main()
