import hashlib
import json
import subprocess
from dataclasses import replace
from pathlib import Path
import pytest
from diamondclock import run_provenance as rp
from diamondclock.physics import Physics
from diamondclock.simulation import Config, simulate
from diamondclock.reporting import export_files
from diamondclock.reference_store import ReferenceStore


def test_changed_source_or_snapshot_is_rejected(tmp_path):
    (tmp_path / "app.py").write_text("original\n")
    context = rp.capture(root=tmp_path)
    rp.validate(context, root=tmp_path)
    (tmp_path / "app.py").write_text("changed\n")
    with pytest.raises(ValueError, match="changed after"):
        rp.validate(context, root=tmp_path)
    context["files"]["app.py"] = b"tampered"
    with pytest.raises(ValueError, match="snapshot"):
        rp.validate(context, root=tmp_path)


def test_process_requires_restart_after_source_change(monkeypatch):
    monkeypatch.setattr(rp, "PROCESS_SOURCES", {})
    with pytest.raises(ValueError, match="Restart"):
        rp.capture()


def test_export_has_bound_snapshot_and_user_references():
    c = Config(n=1024)
    context = rp.capture(config=c, physics=Physics())
    trace, allan, diagnostics = simulate(c)
    store = ReferenceStore()
    added = store.add(dict(title="DOI-less fixture", authors="A", year=2026,
                           journal="Fixture", url="https://example.org/test"))
    files = export_files(trace, allan, c, diagnostics,
                         run_provenance=context, references=store.catalog())
    rp.verify_files(files)
    meta = json.loads(files["metadata.json"])
    assert meta["computation_source_verified"] is True
    assert meta["run_provenance"]["capture_stage"] == "before_calculation"
    assert meta["data_kind"] == "SIMULATION"
    for name, digest in meta["source_sha256"].items():
        assert hashlib.sha256(files["source_snapshot/" + name]).hexdigest() == digest
    assert added["id"] in files["sources.json"].decode()
    assert added["id"] in files["references.bib"].decode()
    assert meta["reference_catalog_sha256"] == hashlib.sha256(files["sources.json"]).hexdigest()
    with pytest.raises(ValueError, match="configuration"):
        export_files(trace, allan, replace(c, seed=c.seed+1), diagnostics,
                     run_provenance=context)
    legacy = export_files(trace, allan, c, diagnostics)
    assert json.loads(legacy["metadata.json"])["computation_source_verified"] is False
    files["config.json"] = b"corrupt"
    with pytest.raises(ValueError, match="Checksum"):
        rp.verify_files(files)


def test_existing_run_is_never_overwritten_and_unsafe_paths_rejected(tmp_path):
    data = b"old"
    files = {"data.csv": data, "SHA256SUMS.txt":
             (hashlib.sha256(data).hexdigest() + "  data.csv\n").encode()}
    out = tmp_path / "run"
    rp.write_run_directory(out, files)
    with pytest.raises(FileExistsError):
        rp.write_run_directory(out, files)
    assert (out / "data.csv").read_bytes() == data
    bad = {"../escape": data, "SHA256SUMS.txt":
           (hashlib.sha256(data).hexdigest() + "  ../escape\n").encode()}
    with pytest.raises(ValueError, match="Unsafe"):
        rp.write_run_directory(tmp_path / "bad", bad)
    assert not (tmp_path / "bad").exists()


def test_historical_baseline_git_blobs_are_unchanged():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "provenance/historical_baseline.json").read_text())
    for name, expected in manifest["files"].items():
        # Git filters account for Windows checkout line endings.
        actual = subprocess.check_output(
            ["git", "-C", str(root), "hash-object", "--path", name, name],
            text=True).strip()
        assert actual == expected, name


def test_manifest_must_cover_every_member_and_reject_windows_paths(tmp_path):
    digest = hashlib.sha256(b"x").hexdigest()
    with pytest.raises(ValueError, match="every bundle member"):
        rp.write_run_directory(tmp_path / "partial", {
            "SHA256SUMS.txt": b"", "../unlisted": b"x"})
    with pytest.raises(ValueError, match="Unsafe"):
        rp.verify_files({"C:/escape": b"x", "SHA256SUMS.txt":
                         (digest + "  C:/escape\n").encode()})
    assert not (tmp_path / "partial").exists()
