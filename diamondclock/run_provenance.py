"""Capture implementation bytes before calculation; never rewrite prior runs."""
import hashlib
import json
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from .resources import project_root
ROOT = project_root()


def source_files(root=ROOT):
    paths = []
    for folder, pattern in (("diamondclock", "*.py"), ("references", "*"),
                            ("docs", "*.md"), ("scripts", "*.py"), ("tests", "*.py")):
        paths.extend(p for p in (root / folder).glob(pattern) if p.is_file())
    paths.extend(p for p in (root / "legacy").rglob("*") if p.is_file())
    paths.extend(root / name for name in
                 ("app.py", "README.md", "pyproject.toml", "requirements.txt",
                  "requirements-dev.txt", "setup.py", "MANIFEST.in") if (root / name).is_file())
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(paths)}


def hashes(files):
    return {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}


def source_fingerprint(root=ROOT):
    return hashlib.sha256(json.dumps(hashes(source_files(root)), sort_keys=True).encode()).hexdigest()


PROCESS_SOURCES = hashes(source_files())


def capture(root=ROOT, stage="before_calculation", config=None, physics=None):
    files = source_files(root)
    if root == ROOT and hashes(files) != PROCESS_SOURCES:
        raise ValueError("Source files changed in this process. Restart the app or CLI before calculating.")
    git = {"commit": None, "dirty": None, "status": "unavailable"}
    try:
        def command(*args):
            return subprocess.check_output(
                ["git", "-C", str(root), *args], stderr=subprocess.DEVNULL,
                timeout=10).decode().strip()
        git = {"commit": command("rev-parse", "HEAD"),
               "dirty": bool(command("status", "--porcelain")),
               "status": "available"}
    except (OSError, subprocess.SubprocessError):
        pass
    return {"captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "capture_stage": stage, "git": git,
            "config": asdict(config) if config is not None else None,
            "physics": asdict(physics) if physics is not None else None,
            "source_sha256": hashes(files), "files": files}


def validate(context, root=ROOT):
    if hashes(context["files"]) != context["source_sha256"]:
        raise ValueError("Captured source snapshot has been altered.")
    if hashes(source_files(root)) != context["source_sha256"]:
        raise ValueError("Source files changed after calculation. Run the simulation again.")


def verify_files(files):
    names = set()
    for line in files["SHA256SUMS.txt"].decode().splitlines():
        digest, name = line.split("  ", 1)
        path = PurePosixPath(name)
        if (path.is_absolute() or ".." in path.parts or "\\" in name
                or ":" in name or name != path.as_posix()):
            raise ValueError("Unsafe checksum path.")
        if name in names or name == "SHA256SUMS.txt":
            raise ValueError("Duplicate or self-referential checksum entry.")
        names.add(name)
        if name not in files or hashlib.sha256(files[name]).hexdigest() != digest:
            raise ValueError("Checksum mismatch: " + name)
    if names != set(files) - {"SHA256SUMS.txt"}:
        raise ValueError("Checksum manifest does not cover every bundle member.")


def write_run_directory(folder, files):
    verify_files(files)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
