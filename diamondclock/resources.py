"""Scientific assets in a source checkout or an installed wheel."""
from pathlib import Path


def project_root():
    candidate=Path(__file__).resolve().parents[1]
    if (candidate/'references/sources.json').is_file():return candidate
    assets=Path(__file__).resolve().parent/'_assets'
    if not (assets/'references/sources.json').is_file():
        raise RuntimeError('DiamondClock scientific assets are missing; reinstall the package.')
    return assets


def default_reference_database():
    root=project_root()
    if root.name=='_assets':return Path.home()/'.diamondclock-lab'/'references.sqlite3'
    return root/'user_data'/'references.sqlite3'
