from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from datetime import datetime
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NoteCreate(BaseModel):
    user_id: int
    text: str

class NoteUpdate(BaseModel):
    user_id: int
    text: str


def init_db():
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # На случай, если таблица уже была создана раньше без user_id
    cursor.execute("PRAGMA table_info(notes)")
    columns = [column[1] for column in cursor.fetchall()]

    if "user_id" not in columns:
        cursor.execute("ALTER TABLE notes ADD COLUMN user_id INTEGER DEFAULT 0")

    conn.commit()
    conn.close()


init_db()


@app.get("/")
def home():
    return {"message": "Backend для заметок работает"}


@app.get("/notes")
def get_notes(user_id: int = Query(...)):
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, text, created_at FROM notes WHERE user_id = ? ORDER BY id DESC",
        (user_id,)
    )

    rows = cursor.fetchall()
    conn.close()

    notes = []

    for row in rows:
        notes.append({
            "id": row[0],
            "text": row[1],
            "created_at": row[2]
        })

    return notes


@app.post("/notes")
def create_note(note: NoteCreate):
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO notes (user_id, text, created_at) VALUES (?, ?, ?)",
        (note.user_id, note.text, datetime.now().isoformat())
    )

    conn.commit()
    conn.close()

    return {"message": "Заметка сохранена"}

@app.delete("/notes/{note_id}")
def delete_note(note_id: int, user_id: int = Query(...)):
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM notes WHERE id = ? AND user_id = ?",
        (note_id, user_id)
    )

    conn.commit()
    deleted_count = cursor.rowcount
    conn.close()

    if deleted_count == 0:
        return {"message": "Заметка не найдена или принадлежит другому пользователю"}

    return {"message": "Заметка удалена"}

@app.put("/notes/{note_id}")
def update_note(note_id: int, note: NoteUpdate):
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE notes SET text = ? WHERE id = ? AND user_id = ?",
        (note.text, note_id, note.user_id)
    )

    conn.commit()
    updated_count = cursor.rowcount
    conn.close()

    if updated_count == 0:
        return {"message": "Заметка не найдена или принадлежит другому пользователю"}

    return {"message": "Заметка обновлена"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)