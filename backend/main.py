from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
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
    title: str
    text: str
    reminder_at: str | None = None


class NoteUpdate(BaseModel):
    user_id: int
    title: str
    text: str
    reminder_at: str | None = None


class NotePinUpdate(BaseModel):
    user_id: int
    pinned: int


class TaskCreate(BaseModel):
    user_id: int
    title: str


class TaskUpdate(BaseModel):
    user_id: int
    title: str
    completed: int


def get_moscow_time():
    return datetime.now(ZoneInfo("Europe/Moscow"))


def get_moscow_time_iso():
    return get_moscow_time().isoformat()


def normalize_reminder_time(reminder_at):
    if not reminder_at:
        return None

    try:
        dt = datetime.fromisoformat(reminder_at)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("Europe/Moscow"))

        return dt.isoformat()
    except Exception:
        return None


def init_db():
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            pinned INTEGER NOT NULL DEFAULT 0,
            reminder_at TEXT DEFAULT NULL,
            reminder_sent INTEGER NOT NULL DEFAULT 0
        )
    """)

    cursor.execute("PRAGMA table_info(notes)")
    note_columns = [column[1] for column in cursor.fetchall()]

    if "user_id" not in note_columns:
        cursor.execute("ALTER TABLE notes ADD COLUMN user_id INTEGER DEFAULT 0")

    if "title" not in note_columns:
        cursor.execute("ALTER TABLE notes ADD COLUMN title TEXT DEFAULT ''")

    if "pinned" not in note_columns:
        cursor.execute("ALTER TABLE notes ADD COLUMN pinned INTEGER DEFAULT 0")

    if "reminder_at" not in note_columns:
        cursor.execute("ALTER TABLE notes ADD COLUMN reminder_at TEXT DEFAULT NULL")

    if "reminder_sent" not in note_columns:
        cursor.execute("ALTER TABLE notes ADD COLUMN reminder_sent INTEGER DEFAULT 0")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


@app.get("/")
def home():
    return {"message": "Backend для заметок и задач работает"}


@app.get("/notes")
def get_notes(user_id: int = Query(...)):
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, text, created_at, pinned, reminder_at, reminder_sent
        FROM notes
        WHERE user_id = ?
        ORDER BY pinned DESC, id DESC
        """,
        (user_id,)
    )

    rows = cursor.fetchall()
    conn.close()

    notes = []

    for row in rows:
        notes.append({
            "id": row[0],
            "title": row[1],
            "text": row[2],
            "created_at": row[3],
            "pinned": row[4],
            "reminder_at": row[5],
            "reminder_sent": row[6]
        })

    return notes


@app.post("/notes")
def create_note(note: NoteCreate):
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    reminder_at = normalize_reminder_time(note.reminder_at)

    cursor.execute(
        """
        INSERT INTO notes 
        (user_id, title, text, created_at, pinned, reminder_at, reminder_sent) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            note.user_id,
            note.title,
            note.text,
            get_moscow_time_iso(),
            0,
            reminder_at,
            0
        )
    )

    conn.commit()
    conn.close()

    return {"message": "Заметка сохранена"}


@app.put("/notes/{note_id}")
def update_note(note_id: int, note: NoteUpdate):
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    reminder_at = normalize_reminder_time(note.reminder_at)
    reminder_sent = 0

    cursor.execute(
        """
        UPDATE notes 
        SET title = ?, text = ?, reminder_at = ?, reminder_sent = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            note.title,
            note.text,
            reminder_at,
            reminder_sent,
            note_id,
            note.user_id
        )
    )

    conn.commit()
    updated_count = cursor.rowcount
    conn.close()

    if updated_count == 0:
        return {"message": "Заметка не найдена или принадлежит другому пользователю"}

    return {"message": "Заметка обновлена"}


@app.put("/notes/{note_id}/pin")
def update_pin(note_id: int, note: NotePinUpdate):
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE notes SET pinned = ? WHERE id = ? AND user_id = ?",
        (note.pinned, note_id, note.user_id)
    )

    conn.commit()
    updated_count = cursor.rowcount
    conn.close()

    if updated_count == 0:
        return {"message": "Заметка не найдена или принадлежит другому пользователю"}

    if note.pinned == 1:
        return {"message": "Заметка закреплена"}

    return {"message": "Заметка откреплена"}


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


@app.get("/reminders/due")
def get_due_reminders():
    now_iso = get_moscow_time_iso()

    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, user_id, title, text, reminder_at
        FROM notes
        WHERE reminder_at IS NOT NULL
        AND reminder_sent = 0
        AND reminder_at <= ?
        ORDER BY reminder_at ASC
        """,
        (now_iso,)
    )

    rows = cursor.fetchall()
    conn.close()

    reminders = []

    for row in rows:
        reminders.append({
            "id": row[0],
            "user_id": row[1],
            "title": row[2],
            "text": row[3],
            "reminder_at": row[4]
        })

    return reminders


@app.put("/reminders/{note_id}/sent")
def mark_reminder_sent(note_id: int):
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE notes SET reminder_sent = 1 WHERE id = ?",
        (note_id,)
    )

    conn.commit()
    conn.close()

    return {"message": "Напоминание отмечено как отправленное"}


@app.get("/tasks")
def get_tasks(user_id: int = Query(...)):
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, completed, created_at
        FROM tasks
        WHERE user_id = ?
        ORDER BY completed ASC, id DESC
        """,
        (user_id,)
    )

    rows = cursor.fetchall()
    conn.close()

    tasks = []

    for row in rows:
        tasks.append({
            "id": row[0],
            "title": row[1],
            "completed": row[2],
            "created_at": row[3]
        })

    return tasks


@app.post("/tasks")
def create_task(task: TaskCreate):
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO tasks (user_id, title, completed, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            task.user_id,
            task.title,
            0,
            get_moscow_time_iso()
        )
    )

    conn.commit()
    conn.close()

    return {"message": "Задача создана"}


@app.put("/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate):
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE tasks
        SET title = ?, completed = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            task.title,
            task.completed,
            task_id,
            task.user_id
        )
    )

    conn.commit()
    updated_count = cursor.rowcount
    conn.close()

    if updated_count == 0:
        return {"message": "Задача не найдена или принадлежит другому пользователю"}

    return {"message": "Задача обновлена"}


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, user_id: int = Query(...)):
    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, user_id)
    )

    conn.commit()
    deleted_count = cursor.rowcount
    conn.close()

    if deleted_count == 0:
        return {"message": "Задача не найдена или принадлежит другому пользователю"}

    return {"message": "Задача удалена"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)