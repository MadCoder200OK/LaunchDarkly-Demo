"""The paired launcher preserves credentials and cleans up its own child processes."""

from collections import namedtuple
import importlib.util
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest


def load_launcher():
    path = Path(__file__).resolve().parents[2] / 'dev.py'
    spec = importlib.util.spec_from_file_location('demo_launcher', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('installed, install_python, expects_install', [
    (True, True, False),
    (False, True, True),
    (False, False, False),
])
def test_old_python_uses_existing_interpreter_or_explicit_homebrew_opt_in(monkeypatch, installed, install_python, expects_install):
    launcher = load_launcher()
    version_info = namedtuple('VersionInfo', ['major', 'minor'])
    monkeypatch.setattr(launcher.sys, 'version_info', version_info(3, 10))
    monkeypatch.setattr(launcher.sys, 'platform', 'darwin')
    monkeypatch.setattr(launcher.shutil, 'which', lambda name: {
        'brew': '/brew/bin/brew', 'python3.12': '/brew/bin/python3.12' if installed else None,
    }.get(name))
    monkeypatch.setattr(launcher.subprocess, 'check_output', lambda command, **_: (
        'Python 3.12.10' if command[-1] == '--version' else '/brew/opt/python@3.13'
    ))
    installs = []
    monkeypatch.setattr(launcher, 'run_checked', lambda command, cwd: installs.append(command))
    launches = []

    def replace_process(executable, argv):
        launches.append((executable, argv))
        raise SystemExit(0)

    monkeypatch.setattr(launcher.os, 'execv', replace_process)
    args = ['--preview', '--frontend-port', '5176']
    if installed or expects_install:
        with pytest.raises(SystemExit, match='0'):
            launcher.check_python(install_python, args)
        expected_python = '/brew/bin/python3.12' if installed else '/brew/opt/python@3.13/bin/python3.13'
        assert launches == [(expected_python, [expected_python, launcher.__file__, *args])]
    else:
        with pytest.raises(launcher.SetupError, match=r'Python 3\.12\+ is required'):
            launcher.check_python(install_python, args)
        assert not launches
    assert installs == ([['/brew/bin/brew', 'install', 'python@3.13']] if expects_install else [])


def test_prepare_preserves_env_and_installs_only_when_inputs_change(tmp_path, monkeypatch):
    launcher = load_launcher()
    (tmp_path / '.venv/bin').mkdir(parents=True)
    (tmp_path / '.venv/bin/python').touch()
    (tmp_path / 'backend').mkdir()
    (tmp_path / 'backend/requirements.lock').write_text('pinned-python-deps')
    frontend = tmp_path / 'frontend'
    (frontend / 'node_modules/vite/bin').mkdir(parents=True)
    (frontend / 'node_modules/vite/bin/vite.js').touch()
    (frontend / 'package.json').write_text('{}')
    (frontend / 'package-lock.json').write_text('{}')
    (tmp_path / '.env.example').write_text('APP_MODE=preview\n')
    secret = 'LOCAL_TEST_PLACEHOLDER=preserve-me\n'
    (tmp_path / '.env').write_text(secret)
    monkeypatch.setattr(launcher.subprocess, 'check_output', lambda command, **_: 'Python 3.13.5' if command[-1] == '--version' and command[0] != 'node' else 'v22.19.0')
    calls = []
    monkeypatch.setattr(launcher, 'run_checked', lambda command, cwd: calls.append(command))
    launcher.prepare(tmp_path, 'node', 'npm')
    launcher.prepare(tmp_path, 'node', 'npm')
    assert len(calls) == 2
    assert (tmp_path / '.env').read_text() == secret
    (frontend / 'package-lock.json').write_text('{"changed":true}')
    launcher.prepare(tmp_path, 'node', 'npm')
    assert len(calls) == 3 and calls[-1][0] == 'npm'
    (tmp_path / '.env').unlink()
    launcher.prepare(tmp_path, 'node', 'npm')
    assert (tmp_path / '.env').read_text() == 'APP_MODE=preview\n'


@pytest.mark.skipif(sys.platform == 'win32', reason='POSIX process-group cleanup')
def test_shutdown_kills_stubborn_child_but_leaves_unrelated_process(tmp_path):
    launcher = load_launcher()
    ready = tmp_path / 'ready'
    child = subprocess.Popen([sys.executable, '-c',
        'import signal,time,pathlib; signal.signal(signal.SIGINT, signal.SIG_IGN); '
        f'pathlib.Path({str(ready)!r}).touch(); time.sleep(30)'], start_new_session=True)
    unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], start_new_session=True)
    try:
        deadline = time.monotonic() + 3
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        assert ready.exists()
        started = time.monotonic()
        launcher.stop_processes([child], grace=.1)
        assert child.poll() is not None and time.monotonic() - started < 2
        assert unrelated.poll() is None
    finally:
        for process in (child, unrelated):
            if process.poll() is None:
                process.kill()
            process.wait()


def test_supervision_stops_on_either_child_exit():
    launcher = load_launcher()
    child = subprocess.Popen([sys.executable, '-c', 'raise SystemExit(7)'])
    child.wait()
    with pytest.raises(launcher.SetupError, match='Frontend stopped.*7'):
        launcher.supervise([('Frontend', child)], 8013, 5176)
