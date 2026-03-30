# Database (SQLite) — Notes + Tags

This container uses **SQLite** for local persistence.

## Database file

- Default DB file: `myapp.db` (in this `database/` folder)

## Schema

### `notes`
Stores notes.

| column | type | notes |
|---|---|---|
| id | INTEGER PK | autoincrement |
| title | TEXT | required |
| content | TEXT | required (default empty string) |
| is_archived | INTEGER | 0/1 flag |
| created_at | TIMESTAMP | default CURRENT_TIMESTAMP |
| updated_at | TIMESTAMP | default CURRENT_TIMESTAMP (kept current via trigger) |

Indexes:
- `idx_notes_updated_at`
- `idx_notes_created_at`

### `tags`
Stores unique tags (case-insensitive).

| column | type | notes |
|---|---|---|
| id | INTEGER PK | autoincrement |
| name | TEXT | unique, `COLLATE NOCASE` |
| created_at | TIMESTAMP | default CURRENT_TIMESTAMP |

Indexes:
- `idx_tags_name`

### `note_tags`
Many-to-many mapping between notes and tags.

| column | type | notes |
|---|---|---|
| note_id | INTEGER | FK -> notes(id), ON DELETE CASCADE |
| tag_id | INTEGER | FK -> tags(id), ON DELETE CASCADE |
| created_at | TIMESTAMP | default CURRENT_TIMESTAMP |

Constraints:
- Composite primary key `(note_id, tag_id)` prevents duplicates.

Indexes:
- `idx_note_tags_note_id`
- `idx_note_tags_tag_id`

## Initialize / update schema

Run:

```bash
cd database
python3 init_db.py
```

The init script is idempotent: safe to run multiple times.

It also writes:
- `db_connection.txt` (connection info)
- `db_visualizer/sqlite.env` (for the included Node DB viewer)

## Inspect with the included shell

```bash
cd database
python3 db_shell.py
```

Useful commands:
- `.tables`
- `.schema notes`
- `.describe tags`
- SQL queries, e.g.
  ```sql
  SELECT n.id, n.title, group_concat(t.name, ', ') AS tags
  FROM notes n
  LEFT JOIN note_tags nt ON nt.note_id = n.id
  LEFT JOIN tags t ON t.id = nt.tag_id
  GROUP BY n.id
  ORDER BY n.updated_at DESC;
  ```
