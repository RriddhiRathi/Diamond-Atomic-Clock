import json
from pathlib import Path
from streamlit.testing.v1 import AppTest
from diamondclock.reference_store import ReferenceStore


def test_paper_persists_across_sessions_and_is_exported():
    app = str(Path(__file__).resolve().parents[1] / "app.py")
    at = AppTest.from_file(app, default_timeout=90).run()
    assert not at.exception
    def text(label, value):
        next(item for item in at.text_input if item.label == label).set_value(value)
    text("Title", "Dashboard saved fixture")
    text("Authors", "A. Tester")
    text("Journal or publication", "Fixture")
    text("DOI (optional)", "10.1234/dashboard")
    text("Paper URL", "https://example.org/dashboard")
    next(button for button in at.button if button.label == "Add paper").click().run()
    assert not at.exception
    assert len(ReferenceStore().papers()) == 1
    fresh = AppTest.from_file(app, default_timeout=90).run()
    assert not fresh.exception
    assert any("Dashboard saved fixture" in expander.label for expander in fresh.expander)
    assert any("Unverified user reference" in str(item.value) for item in fresh.markdown)
    assert not any("Verified source" in str(item.value) for item in fresh.markdown)
    fresh.button(key="prepare_export").click().run()
    assert not fresh.exception
    files = fresh.session_state["export"][1]
    rows = json.loads(files["sources.json"])
    assert any(row["title"] == "Dashboard saved fixture"
               and row["verification_status"] == "unverified" for row in rows)
    assert b"Dashboard saved fixture" in files["references.bib"]
