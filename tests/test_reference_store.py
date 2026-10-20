import json
import sqlite3
import pytest
from diamondclock.reference_store import (
    ReferenceStore, curated_sources, verification_label, catalog_bytes, bibtex_bytes)


def paper(**changes):
    values = dict(title="Unverified test paper", authors="A. Researcher", year=2026,
                  journal="Test journal", doi="10.1234/test", url="https://example.org/paper",
                  note="Regression fixture; not a research source.")
    values.update(changes)
    return values


def test_persistence_duplicates_and_no_verification_promotion(tmp_path):
    path = tmp_path / "papers.sqlite3"
    first = ReferenceStore(path).add(paper(verified="2026-10-20",
                verification_status="curated_record", implementation="physics.py"))
    restored = ReferenceStore(path).papers()[0]
    assert restored == first
    assert restored["verification_status"] == "unverified"
    assert restored["verified"] is None
    assert restored["implementation"] == "Not mapped"
    assert "Unverified" in verification_label(restored)
    with pytest.raises(ValueError, match="already saved"):
        ReferenceStore(path).add(paper(doi="https://doi.org/10.1234/TEST"))
    assert len(ReferenceStore(path).papers()) == 1


def test_user_payload_cannot_claim_curated_status(tmp_path):
    path = tmp_path / "papers.sqlite3"
    store = ReferenceStore(path)
    row = store.add(paper())
    row.update(verification_status="curated_record", verified="2026-10-20")
    with sqlite3.connect(path) as db:
        db.execute("UPDATE papers SET payload=?", (json.dumps(row),))
    assert store.papers()[0]["verification_status"] == "unverified"


@pytest.mark.parametrize("changes", [
    {"doi": "not-a-doi"}, {"url": "javascript:alert(1)"},
    {"url": "/relative"}, {"title": " "}, {"year": 1799},
    {"doi": "10.1103/PhysRevApplied.19.064084"},
])
def test_invalid_or_duplicate_curated_input(changes):
    with pytest.raises(ValueError):
        ReferenceStore().add(paper(**changes))


def test_doiless_export_and_curated_labels():
    store = ReferenceStore()
    row = store.add(paper(doi=""))
    catalog = store.catalog()
    assert row in json.loads(catalog_bytes(catalog))
    bib = bibtex_bytes(catalog).decode()
    assert row["id"] in bib and row["url"] in bib
    assert "Unverified user reference" in bib
    model = next(s for s in curated_sources() if s["id"] == "MODEL")
    assert "not a publication" in verification_label(model)
    assert "recorded review date" in verification_label(curated_sources()[0])
