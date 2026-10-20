"""Persistent local Paper Bucket. A DOI is an identifier, not verification."""
import json
import os
import re
import sqlite3
import uuid
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def curated_sources():
    rows = json.loads((ROOT / "references/sources.json").read_text(encoding="utf-8"))
    for row in rows:
        row["verification_status"] = (
            "model_assumption" if row["id"] == "MODEL" else "curated_record")
        row["verification_origin"] = "repository"
    return rows


def verification_label(row):
    if row.get("verification_status") == "model_assumption":
        return "Model assumption / numerical method; not a publication"
    if row.get("verification_status") == "curated_record":
        return "Repository-curated; recorded review date: " + str(row.get("verified", "unknown"))
    return "Unverified user reference; not mapped to the scientific model"


def normalize_doi(value):
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "",
                   str(value or "").strip(), flags=re.I)
    if value and not re.fullmatch(r"10\.\d{4,9}/[^\s]+", value):
        raise ValueError("DOI must have the form 10.xxxx/suffix; this checks syntax only.")
    return value.lower()


def database_path():
    return Path(os.environ.get("DIAMONDCLOCK_REFERENCE_DB",
                               str(ROOT / "user_data/references.sqlite3")))


class ReferenceStore:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS papers "
                       "(fingerprint TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=20)

    def papers(self):
        with self.connect() as db:
            rows = [json.loads(row[0]) for row in db.execute(
                "SELECT payload FROM papers ORDER BY fingerprint")]
        for row in rows:
            row.update(verification_status="unverified", verification_origin="user",
                       verified=None, implementation="Not mapped", locator="User supplied")
        return rows

    def catalog(self):
        return curated_sources() + self.papers()

    def add(self, values):
        row = {key: str(values.get(key, "") or "").strip()
               for key in ("title", "authors", "journal", "url", "note")}
        if any(not row[key] for key in ("title", "authors", "journal", "url")):
            raise ValueError("Title, authors, journal, and paper URL are required.")
        try:
            year = int(values.get("year", 0))
        except (TypeError, ValueError):
            raise ValueError("Publication year must be an integer.") from None
        if not 1800 <= year <= 2100:
            raise ValueError("Publication year must be between 1800 and 2100.")
        url = urlsplit(row["url"])
        if url.scheme not in ("https", "http") or not url.netloc:
            raise ValueError("Paper URL must be an absolute HTTP or HTTPS URL.")
        doi = normalize_doi(values.get("doi"))
        fingerprint = "doi:" + doi if doi else "url:" + row["url"]
        if doi and any(normalize_doi(s.get("doi")) == doi for s in curated_sources()):
            raise ValueError("This DOI is already in the curated bibliography.")
        row.update(id="USER-" + uuid.uuid4().hex, year=year, doi=doi or None,
                   evidence="User-added reference", verified=None,
                   verification_status="unverified", verification_origin="user",
                   locator="User supplied", implementation="Not mapped")
        try:
            with self.connect() as db:
                db.execute("INSERT INTO papers VALUES (?, ?)",
                           (fingerprint, json.dumps(row, ensure_ascii=False)))
        except sqlite3.IntegrityError:
            raise ValueError("This reference is already saved.") from None
        return row


def catalog_bytes(rows):
    return json.dumps(rows, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8")


def bibtex_bytes(rows):
    def escape(value):
        return str(value or "").replace("\\", r"\textbackslash{}").replace(
            "{", r"\{").replace("}", r"\}").replace("\n", " ")
    entries = []
    for row in rows:
        fields = {key: row.get(key) for key in ("title", "author", "year", "journal", "doi", "url")}
        fields["author"] = row.get("authors")
        fields["note"] = verification_label(row) + "; " + str(row.get("note", ""))
        entries.append("@misc{" + row["id"] + ",\n" + ",\n".join(
            "  " + key + " = {" + escape(value) + "}"
            for key, value in fields.items() if value is not None) + "\n}\n")
    return "\n".join(entries).encode("utf-8")
