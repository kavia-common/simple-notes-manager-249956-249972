#!/usr/bin/env python3
"""Initialize SQLite database for database.

This initializer is responsible for creating the SQLite database file (if missing)
and ensuring the schema exists.

Notes app schema:
- notes: stores note content
- tags: stores unique tags
- note_tags: many-to-many join table between notes and tags

The script is designed to be idempotent and safe to re-run.
"""

import os
import sqlite3

DB_NAME = "myapp.db"
DB_USER = "kaviasqlite"  # Not used for SQLite, but kept for consistency
DB_PASSWORD = "kaviadefaultpassword"  # Not used for SQLite, but kept for consistency
DB_PORT = "5000"  # Not used for SQLite, but kept for consistency


def _enable_sqlite_pragmas(cursor: sqlite3.Cursor) -> None:
    """Enable recommended SQLite pragmas."""
    # Enforce FK constraints
    cursor.execute("PRAGMA foreign_keys = ON")
    # Better concurrent behavior for typical web/API usage
    cursor.execute("PRAGMA journal_mode = WAL")
    # Reasonable sync mode for local dev; change if you need max durability
    cursor.execute("PRAGMA synchronous = NORMAL")


def _create_schema(cursor: sqlite3.Cursor) -> None:
    """Create all required tables/indexes (idempotent)."""
    # Minimal metadata table (kept from template)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS app_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Notes
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            is_archived INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Tags (unique by name, case-insensitive via COLLATE NOCASE)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name)
        )
        """
    )

    # Join table for many-to-many note<->tag relationship
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS note_tags (
            note_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (note_id, tag_id),
            FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
        """
    )

    # Helpful indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_updated_at ON notes(updated_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_note_tags_note_id ON note_tags(note_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_note_tags_tag_id ON note_tags(tag_id)")

    # Trigger to keep notes.updated_at current on updates
    cursor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_notes_updated_at
        AFTER UPDATE ON notes
        FOR EACH ROW
        BEGIN
            UPDATE notes
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = NEW.id;
        END
        """
    )


def _seed_app_info(cursor: sqlite3.Cursor) -> None:
    """Seed basic metadata rows (idempotent)."""
    cursor.execute(
        "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)",
        ("project_name", "database"),
    )
    cursor.execute(
        "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)",
        ("version", "0.1.0"),
    )
    cursor.execute(
        "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)",
        ("author", "John Doe"),
    )
    cursor.execute(
        "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)",
        ("description", "SQLite DB for the Notes app (notes + tags)."),
    )


def _seed_sample_notes_and_tags(cursor: sqlite3.Cursor) -> None:
    """Insert some minimal sample data (safe to re-run).

    We only insert seed data when there are no notes yet.
    """
    cursor.execute("SELECT COUNT(1) FROM notes")
    if int(cursor.fetchone()[0]) > 0:
        return

    # Notes
    cursor.execute(
        """
        INSERT INTO notes (title, content)
        VALUES (?, ?)
        """,
        (
            "Welcome",
            "This is your first note. You can edit it, tag it, or delete it.",
        ),
    )
    cursor.execute(
        """
        INSERT INTO notes (title, content)
        VALUES (?, ?)
        """,
        (
            "Tagging",
            "Try adding tags like 'work' or 'personal' to organize notes.",
        ),
    )

    # Tags
    for tag in ["welcome", "tips"]:
        cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))

    # Map tags to first note
    cursor.execute("SELECT id FROM notes ORDER BY id ASC LIMIT 1")
    first_note_id = cursor.fetchone()[0]

    cursor.execute("SELECT id FROM tags WHERE name = ?", ("welcome",))
    tag_welcome_id = cursor.fetchone()[0]
    cursor.execute("SELECT id FROM tags WHERE name = ?", ("tips",))
    tag_tips_id = cursor.fetchone()[0]

    cursor.execute(
        "INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)",
        (first_note_id, tag_welcome_id),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)",
        (first_note_id, tag_tips_id),
    )


def _write_connection_files(db_name: str) -> None:
    """Write db_connection.txt and db_visualizer/sqlite.env for local tooling."""
    current_dir = os.getcwd()
    connection_string = f"sqlite:///{current_dir}/{db_name}"

    try:
        with open("db_connection.txt", "w", encoding="utf-8") as f:
            f.write("# SQLite connection methods:\n")
            f.write(f"# Python: sqlite3.connect('{db_name}')\n")
            f.write(f"# Connection string: {connection_string}\n")
            f.write(f"# File path: {current_dir}/{db_name}\n")
        print("Connection information saved to db_connection.txt")
    except Exception as e:
        print(f"Warning: Could not save connection info: {e}")

    # Create environment variables file for Node.js viewer
    db_path = os.path.abspath(db_name)

    if not os.path.exists("db_visualizer"):
        os.makedirs("db_visualizer", exist_ok=True)
        print("Created db_visualizer directory")

    try:
        with open("db_visualizer/sqlite.env", "w", encoding="utf-8") as f:
            f.write(f'export SQLITE_DB="{db_path}"\n')
        print("Environment variables saved to db_visualizer/sqlite.env")
    except Exception as e:
        print(f"Warning: Could not save environment variables: {e}")


print("Starting SQLite setup...")

db_exists = os.path.exists(DB_NAME)
if db_exists:
    print(f"SQLite database already exists at {DB_NAME}")
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute("SELECT 1")
        conn.close()
        print("Database is accessible and working.")
    except Exception as e:
        print(f"Warning: Database exists but may be corrupted: {e}")
else:
    print("Creating new SQLite database...")

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

_enable_sqlite_pragmas(cursor)
_create_schema(cursor)
_seed_app_info(cursor)
_seed_sample_notes_and_tags(cursor)

conn.commit()

# Stats
cursor.execute(
    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
)
table_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM notes")
notes_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM tags")
tags_count = cursor.fetchone()[0]

conn.close()

_write_connection_files(DB_NAME)

current_dir = os.getcwd()
connection_string = f"sqlite:///{current_dir}/{DB_NAME}"

print("\nSQLite setup complete!")
print(f"Database: {DB_NAME}")
print(f"Location: {current_dir}/{DB_NAME}")
print("")

print("To use with Node.js viewer, run: source db_visualizer/sqlite.env")

print("\nTo connect to the database, use one of the following methods:")
print(f"1. Python: sqlite3.connect('{DB_NAME}')")
print(f"2. Connection string: {connection_string}")
print(f"3. Direct file access: {current_dir}/{DB_NAME}")
print("")

print("Database statistics:")
print(f"  Tables: {table_count}")
print(f"  Notes: {notes_count}")
print(f"  Tags: {tags_count}")

try:
    import subprocess

    result = subprocess.run(["which", "sqlite3"], capture_output=True, text=True)
    if result.returncode == 0:
        print("")
        print("SQLite CLI is available. You can also use:")
        print(f"  sqlite3 {DB_NAME}")
except Exception:
    pass

print("\nScript completed successfully.")
