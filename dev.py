"""One-command local setup, startup, and shutdown. Run: python3 dev.py."""

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
import venv


ROOT = Path(__file__).resolve().parent
MIN_PYTHON = (3, 12)
MAC_PYTHON_FORMULA = 'python@3.13'


class SetupError(Exception):
    """A readable setup failure, without dumping environment variables or secrets."""


def run_checked(command, cwd):
    result = subprocess.run(command, cwd=cwd)
    if result.returncode:
        raise SetupError('Dependency setup failed. Resolve the error above and run again.')


def signature(*paths):
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def needs_install(stamp, expected):
    return not stamp.exists() or stamp.read_text().strip() != expected


def python_version(version):
    """Read major and minor from the output of Python's --version option."""
    return tuple(map(int, version.split()[1].split('.')[:2]))


def check_python(install_python, argv):
    if sys.version_info[:2] >= MIN_PYTHON:
        return
    if sys.platform == 'darwin':
        for name in ('python3.13', 'python3.12'):
            executable = shutil.which(name)
            if executable and python_version(subprocess.check_output([executable, '--version'], text=True)) >= MIN_PYTHON:
                os.execv(executable, [executable, str(Path(__file__).resolve()), *argv])
        if install_python:
            brew = shutil.which('brew')
            if not brew:
                raise SetupError('Homebrew is required for --install-python. Install Homebrew or use an existing Python 3.12+ interpreter.')
            print('Installing Python 3.13 alongside your current Python…', flush=True)
            run_checked([brew, 'install', MAC_PYTHON_FORMULA], ROOT)
            prefix = subprocess.check_output([brew, '--prefix', MAC_PYTHON_FORMULA], text=True).strip()
            executable = str(Path(prefix) / 'bin/python3.13')
            os.execv(executable, [executable, str(Path(__file__).resolve()), *argv])
        raise SetupError(
            f'Python 3.12+ is required. This command is running Python {sys.version_info.major}.{sys.version_info.minor}.\n'
            f'With Homebrew installed, rerun with `--install-python` or run `brew install {MAC_PYTHON_FORMULA}` and use `python3.13`.'
        )
    raise SetupError('Python 3.12+ is required. Run this launcher with a supported Python interpreter.')


# DEMO START local-setup: Prepare dependencies once and preserve the user's local credentials.
def prepare(root, node, npm):
    python = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        print('Creating the Python environment…', flush=True)
        venv.create(root / '.venv', with_pip=True)
    version = subprocess.check_output([str(python), '--version'], text=True).strip()
    if python_version(version) < MIN_PYTHON:
        raise SetupError(f'The existing .venv uses {version}. Move it aside and rerun the launcher to create a Python 3.12+ environment.')

    lock = root / 'backend/requirements.lock'
    python_stamp = root / '.venv/.demo-requirements.sha256'
    python_signature = signature(lock) + version
    if needs_install(python_stamp, python_signature):
        print('Installing Python dependencies…', flush=True)
        run_checked([str(python), '-m', 'pip', 'install', '--cache-dir', str(root / '.demo-cache/pip'), '-r', str(lock)], root)
        python_stamp.write_text(python_signature)

    frontend = root / 'frontend'
    node_version = subprocess.check_output([node, '--version'], text=True).strip()
    node_stamp = frontend / 'node_modules/.demo-dependencies.sha256'
    node_signature = signature(frontend / 'package.json', frontend / 'package-lock.json') + node_version
    if not (frontend / 'node_modules/vite/bin/vite.js').exists() or needs_install(node_stamp, node_signature):
        print('Installing frontend dependencies…', flush=True)
        run_checked([npm, 'ci', '--no-fund', '--cache', str(root / '.demo-cache/npm')], frontend)
        node_stamp.write_text(node_signature)

    # Exclusive creation cannot overwrite a key even if another setup process creates .env first.
    try:
        with (root / '.env').open('x') as output:
            output.write((root / '.env.example').read_text())
        print('Created .env with safe preview defaults.', flush=True)
    except FileExistsError:
        pass
    return python
# DEMO END local-setup


def check_port(port):
    with socket.socket() as listener:
        try:
            listener.bind(('127.0.0.1', port))
        except OSError:
            raise SetupError(f'Port {port} is busy. Stop the existing demo in your IDE/terminal, or choose different --backend-port and --frontend-port values.') from None


# DEMO START paired-shutdown: Stop only the two children this launcher owns, with a bounded wait.
def stop_processes(processes, grace=8):
    active = [process for process in processes if process.poll() is None]
    for process in active:
        try:
            if os.name == 'posix':
                os.killpg(process.pid, signal.SIGINT)
            else:
                process.terminate()
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + grace
    for process in active:
        try:
            process.wait(timeout=max(0.01, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            try:
                if os.name == 'posix':
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
            except ProcessLookupError:
                pass
            process.wait()
# DEMO END paired-shutdown


def supervise(processes, backend_port, frontend_port, startup_timeout=25):
    pending = {f'http://127.0.0.1:{backend_port}/api/health', f'http://127.0.0.1:{frontend_port}/'}
    deadline = time.monotonic() + startup_timeout
    announced = False
    while True:
        for name, process in processes:
            if process.poll() is not None:
                raise SetupError(f'{name} stopped (exit {process.returncode}). Both demo services are stopping.')
        if not announced:
            for url in tuple(pending):
                try:
                    with urlopen(url, timeout=0.3) as response:
                        if response.status == 200:
                            pending.remove(url)
                except (URLError, TimeoutError, OSError):
                    pass
            if not pending:
                print(f'\nDemo ready → http://127.0.0.1:{frontend_port}\nCtrl+C stops both services.\n', flush=True)
                announced = True
            elif time.monotonic() > deadline:
                raise SetupError('Startup timed out. Check the service messages above, then run again.')
        time.sleep(0.2)


# DEMO START paired-startup: Start Python and Vite together without touching existing IDE processes.
def main(argv=None):
    parser = argparse.ArgumentParser(description='Set up and start the complete ABC Bank demo.')
    parser.add_argument('--backend-port', type=int, default=8000)
    parser.add_argument('--frontend-port', type=int, default=5173)
    parser.add_argument('--preview', action='store_true', help='Run without cloud calls, preserving .env')
    parser.add_argument('--install-python', action='store_true', help='Use Homebrew on macOS to install Python 3.13 if needed')
    argv = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(argv)
    processes = []
    previous_term = signal.getsignal(signal.SIGTERM)
    previous_int = signal.getsignal(signal.SIGINT)

    def interrupted(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    try:
        check_python(args.install_python, argv)
        node, npm = shutil.which('node'), shutil.which('npm')
        if not node or not npm:
            raise SetupError('Install Node.js 22.12+ and npm, then run again.')
        version = subprocess.check_output([node, '--version'], text=True).strip().lstrip('v')
        if tuple(map(int, version.split('.')[:2])) < (22, 12):
            raise SetupError('Use Node.js 22.12 or later.')
        if args.backend_port == args.frontend_port or not all(1 <= port <= 65535 for port in (args.backend_port, args.frontend_port)):
            raise SetupError('Choose two different ports between 1 and 65535.')
        for port in (args.backend_port, args.frontend_port):
            check_port(port)
        python = prepare(ROOT, node, npm)
        environment = os.environ.copy()
        environment['PYTHONPATH'] = str(ROOT / 'backend') + os.pathsep + environment.get('PYTHONPATH', '')
        environment['DEMO_API_PORT'] = str(args.backend_port)
        if args.preview:
            environment.update(APP_MODE='preview', AI_ENABLED='false')
        options = {'cwd': ROOT, 'env': environment, 'start_new_session': os.name == 'posix'}
        backend = subprocess.Popen([str(python), '-m', 'app.run', '--port', str(args.backend_port)], **options)
        processes.append(('Backend', backend))
        # Direct Node invocation avoids an npm shell/grandchild that could outlive Ctrl+C.
        frontend = subprocess.Popen([node, str(ROOT / 'frontend/node_modules/vite/bin/vite.js'),
                                     '--host', '127.0.0.1', '--port', str(args.frontend_port), '--strictPort'],
                                    **{**options, 'cwd': ROOT / 'frontend'})
        processes.append(('Frontend', frontend))
        supervise(processes, args.backend_port, args.frontend_port)
    except KeyboardInterrupt:
        print('\nStopping the demo…', flush=True)
    except (SetupError, OSError, subprocess.SubprocessError) as error:
        print(f'\n{error}', file=sys.stderr)
        return 1
    finally:
        # A second stop request must not interrupt cleanup and leave a child running.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        try:
            stop_processes([process for _, process in processes])
        finally:
            signal.signal(signal.SIGINT, previous_int)
            signal.signal(signal.SIGTERM, previous_term)
    return 0
# DEMO END paired-startup


if __name__ == '__main__':
    raise SystemExit(main())
