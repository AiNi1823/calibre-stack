"""Database operations for calibre metadata."""

import sqlite3
from contextlib import contextmanager


class CalibreDB:
    """Calibre database wrapper."""

    def __init__(self, db_path):
        self.db_path = db_path

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def get_all_books(self):
        """Get all books with their metadata."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT b.id, b.title, b.sort, b.has_cover, b.pubdate, b.isbn,
                       b.path, b.last_modified,
                       GROUP_CONCAT(DISTINCT a.name) as authors
                FROM books b
                LEFT JOIN books_authors_link bal ON b.id = bal.book
                LEFT JOIN authors a ON bal.author = a.id
                GROUP BY b.id
                ORDER BY b.id
            """)
            return [dict(row) for row in c.fetchall()]

    def get_book_by_id(self, book_id):
        """Get a single book by ID."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT b.id, b.title, b.sort, b.has_cover, b.pubdate, b.isbn,
                       b.path, b.last_modified,
                       GROUP_CONCAT(DISTINCT a.name) as authors
                FROM books b
                LEFT JOIN books_authors_link bal ON b.id = bal.book
                LEFT JOIN authors a ON bal.author = a.id
                WHERE b.id = ?
                GROUP BY b.id
            """, (book_id,))
            row = c.fetchone()
            return dict(row) if row else None

    def get_missing_fields(self, book):
        """Check which fields are missing for a book."""
        missing = []
        if not book.get("isbn"):
            missing.append("isbn")
        if book.get("pubdate", "9999") < "1900-01-01":
            missing.append("pubdate")
        if not self.has_description(book["id"]):
            missing.append("description")
        if not book.get("has_cover"):
            missing.append("cover")
        return missing

    def has_description(self, book_id):
        """Check if a book has a description."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("SELECT count(*) FROM comments WHERE book=?", (book_id,))
            return c.fetchone()[0] > 0

    def update_book(self, book_id, updates):
        """Update book metadata fields."""
        with self.connect() as conn:
            c = conn.cursor()
            # Drop triggers that call title_sort()
            c.execute("DROP TRIGGER IF EXISTS books_update_trg")
            c.execute("DROP TRIGGER IF EXISTS books_insert_trg")

            set_clauses = []
            params = []
            for key, value in updates.items():
                set_clauses.append(f"{key} = ?")
                params.append(value)
            params.append(book_id)

            c.execute(f"UPDATE books SET {', '.join(set_clauses)} WHERE id = ?", params)

            # Recreate triggers
            c.execute("""CREATE TRIGGER books_insert_trg AFTER INSERT ON books
                BEGIN UPDATE books SET sort=title_sort(NEW.title),uuid=uuid4() WHERE id=NEW.id; END""")
            c.execute("""CREATE TRIGGER books_update_trg AFTER UPDATE ON books
                BEGIN UPDATE books SET sort=title_sort(NEW.title) WHERE id=NEW.id AND OLD.title <> NEW.title; END""")

            conn.commit()

    def add_description(self, book_id, text):
        """Add a description to a book."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO comments (book, text) VALUES (?, ?)", (book_id, text[:5000]))
            conn.commit()

    def add_tag(self, book_id, tag_name):
        """Add a tag to a book."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
            c.execute("SELECT id FROM tags WHERE name=?", (tag_name,))
            tag_id = c.fetchone()[0]
            c.execute("INSERT OR IGNORE INTO books_tags_link (book, tag) VALUES (?, ?)", (book_id, tag_id))
            conn.commit()

    def get_book_path(self, book):
        """Get the full filesystem path for a book."""
        import os
        base = os.path.dirname(self.db_path)
        return os.path.join(base, book["path"])

    def get_existing_tags(self, book_id):
        """Get existing tags for a book."""
        with self.connect() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT t.name FROM tags t
                JOIN books_tags_link btl ON t.id = btl.tag
                WHERE btl.book = ?
            """, (book_id,))
            return {row[0] for row in c.fetchall()}
