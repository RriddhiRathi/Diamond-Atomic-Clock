"""Real editable and wheel installation checks outside pytest's repository pythonpath."""
from pathlib import Path
import os,subprocess,sys,venv,tomllib


def test_declared_dependencies_match_requirements_and_package_scope():
    root=Path(__file__).resolve().parents[1]
    data=tomllib.loads((root/'pyproject.toml').read_text())
    required=[x for x in (root/'requirements.txt').read_text().splitlines() if x and not x.startswith('#')]
    assert sorted(required)==sorted(data['project']['dependencies'])
    assert data['tool']['setuptools']['packages']['find']['include']==['diamondclock*']
    assert data['project']['optional-dependencies']['dev']


def test_editable_and_wheel_assets_in_clean_environment(tmp_path):
    root=Path(__file__).resolve().parents[1];env=tmp_path/'venv'
    # Do not inherit site packages: nested venvs need their own build/runtime deps.
    venv.EnvBuilder(with_pip=True).create(env)
    executable=env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    environment=dict(os.environ);environment.pop('PYTHONPATH',None)
    environment['DIAMONDCLOCK_REFERENCE_DB']=str(tmp_path/'refs.sqlite3')
    def run(*arguments):
        p=subprocess.run([str(executable),*arguments],cwd=tmp_path,env=environment,capture_output=True,text=True,timeout=600)
        assert p.returncode==0,p.stdout+'\n'+p.stderr
        return p
    run('-m','pip','install','-e',str(root))
    run('-m','pip','check')
    run('-I','-c','import diamondclock; from diamondclock.resources import project_root; assert (project_root()/"references/sources.json").is_file()')
    wheels=tmp_path/'wheels'
    # Build into a temporary target, avoiding dependence on current working directory.
    run('-m','pip','wheel','--no-deps','--wheel-dir',str(wheels),str(root))
    wheel=next(wheels.glob('*.whl'))
    # A separate environment prevents the editable install masking wheel defects.
    env=tmp_path/'wheel_venv'
    venv.EnvBuilder(with_pip=True).create(env)
    executable=env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    run('-m','pip','install',str(wheel))
    run('-m','pip','check')
    code='''import diamondclock
from pathlib import Path
from diamondclock.resources import project_root
from diamondclock.clock_parameters import ClockExperiment
from diamondclock.clock_reporting import calculate_clock,export_clock
from diamondclock.run_provenance import verify_files
root=project_root()
assert root.name=="_assets",root
assert (root/"legacy/matlab/intern_odmr_as_supplied.m.txt").is_file()
assert (root/"references/clock_equation_map.md").is_file()
c=ClockExperiment(cycles=4,maximum_time_s=3)
r=calculate_clock(c)
f=export_clock(r,c)
verify_files(f)
assert "source_snapshot/diamondclock/clock_simulation.py" in f
'''
    run('-I','-c',code)
