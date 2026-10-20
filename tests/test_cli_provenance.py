import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from diamondclock.reference_store import ReferenceStore
from diamondclock.simulation import Config
from diamondclock.run_provenance import verify_files


def test_cli_exports_saved_catalog_and_refuses_reusing_output(tmp_path):
    root = Path(__file__).resolve().parents[1]
    paper = ReferenceStore().add(dict(title="CLI fixture", authors="A", year=2026,
                        journal="Fixture", url="https://example.org/cli"))
    config = tmp_path / "config.json"
    config.write_text(json.dumps(asdict(Config(n=1024))))
    output = tmp_path / "new-run"
    command = [sys.executable, str(root / "scripts/run_simulation.py"),
               "--config", str(config), "--out", str(output)]
    first = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=90)
    assert first.returncode == 0, first.stderr
    files = {p.relative_to(output).as_posix(): p.read_bytes()
             for p in output.rglob("*") if p.is_file()}
    verify_files(files)
    assert paper["id"] in files["sources.json"].decode()
    assert json.loads(files["metadata.json"])["computation_source_verified"] is True
    second = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=90)
    assert second.returncode != 0
    assert "already exists" in second.stderr
    assert files == {p.relative_to(output).as_posix(): p.read_bytes()
                     for p in output.rglob("*") if p.is_file()}
