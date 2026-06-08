from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NoteCreate(BaseModel):
    text: str


def init_db():
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


@app.get("/")
def home():
    return {"message": "Backend для заметок работает"}


@app.get("/notes")
def get_notes():
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, text, created_at FROM notes ORDER BY id DESC")
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
        "INSERT INTO notes (text, created_at) VALUES (?, ?)",
        (note.text, datetime.now().isoformat())
    )

    conn.commit()
    conn.close()

    return {"message": "Заметка сохранена"}


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)