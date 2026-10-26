import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DB_PATH = PROJECT_ROOT / "backend/db/RequirementsDB.db"


def create_table():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS AppendixSections(
            id INTEGER PRIMARY KEY,
            questionId INTEGER NOT NULL,
            sectionId INTEGER NOT NULL,
            header TEXT,
            content TEXT
        )
        """
    )

    con.commit()
    con.close()


def create_section(question_id: int, section: dict[str, str | None]):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    section_id = section["id"]
    header = section["header"]
    content = section["content"]

    cur.execute(
        "INSERT INTO AppendixSections (questionId, sectionId, header, content) VALUES (?, ?, ?, ?)",
        (question_id, section_id, header, content),
    )

    con.commit()
    con.close()


def check_question_for_sections(question_id: int):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    res = cur.execute(
        "SELECT * FROM AppendixSections WHERE questionId = ?", (question_id,)
    )

    sections = res.fetchall()
    con.close()

    return bool(sections)


def delete_all_sections_for_question(question_id):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("DELETE FROM AppendixSections WHERE questionId = ?", (question_id,))

    con.commit()
    con.close()
