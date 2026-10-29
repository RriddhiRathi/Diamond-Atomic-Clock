"""Keep regression runs independent of a developer's persistent bibliography."""
import pytest


@pytest.fixture(autouse=True)
def isolated_reference_database(tmp_path, monkeypatch):
    monkeypatch.setenv("DIAMONDCLOCK_REFERENCE_DB", str(tmp_path / "references.sqlite3"))


@pytest.fixture
def research_app():
    """Open the preserved workspace through the redesigned app's public navigation."""
    from pathlib import Path
    from streamlit.testing.v1 import AppTest

    def open_workspace(workspace='Stability & compensation', timeout=120):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'),
                                default_timeout=timeout).run()
        app.sidebar.radio(key='dashboard_section').set_value('Research Tools').run()
        if workspace != 'Stability & compensation':
            app.selectbox(key='research_workspace').set_value(workspace).run()
        if workspace == 'Stability & compensation':
            app.button(key='run_legacy').click().run()
        assert not app.exception
        return app
    return open_workspace
