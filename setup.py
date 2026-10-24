"""Include a reproducible scientific source/asset snapshot in installed wheels."""
from pathlib import Path
import shutil
from setuptools import setup
from setuptools.command.build_py import build_py


class ScientificBuild(build_py):
    def run(self):
        super().run()
        if getattr(self,'editable_mode',False):return
        root=Path(__file__).parent
        target=Path(self.build_lib)/'diamondclock'/'_assets'
        paths=[]
        for folder,pattern in [('diamondclock','*.py'),('docs','*.md'),('references','*'),
                               ('scripts','*.py'),('tests','*.py'),('provenance','*.json')]:
            paths.extend(p for p in (root/folder).glob(pattern) if p.is_file())
        paths.extend(p for p in (root/'legacy').rglob('*') if p.is_file())
        paths.extend(root/p for p in ['README.md','app.py','pyproject.toml','setup.py','MANIFEST.in',
                     'requirements.txt','requirements-dev.txt'] if (root/p).is_file())
        for source in paths:
            destination=target/source.relative_to(root)
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,destination)


setup(cmdclass={'build_py':ScientificBuild})
