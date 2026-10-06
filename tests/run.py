#!/usr/bin/env python3
"""Run exact project QML with pinned inert imports in a fresh offscreen workspace."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/offscreen'
DEFAULT_TESTS = ['test_cache_contract', 'test_provider_order_and_clicks',
                 'test_missing_icon_then_pi', 'test_same_provider_fallback', 'test_states']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(base):
    base = base.resolve()
    installed = Path.home() / '.config/omarchy/plugins'
    installed = installed.resolve()
    if ROOT == installed or installed in ROOT.parents:
        raise ValueError('Run from a source checkout, not an installed plugin')
    if base == ROOT or ROOT in base.parents or base == installed or installed in base.parents:
        raise ValueError('Output parent must be outside project and installed plugin directories')
    imports = FIXTURE / 'imports'
    lock = json.loads((FIXTURE / 'imports-lock.json').read_text())
    if any(p.is_symlink() for p in FIXTURE.rglob('*')) or FIXTURE.is_symlink():
        raise ValueError('Fixture symlink; review dependencies before running')
    actual = {str(p.relative_to(imports)): digest(p) for p in imports.rglob('*') if p.is_file()}
    if actual != lock:
        raise ValueError('Fixture lock mismatch; review dependencies before running')
    base.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='agents-offscreen-', dir=base))
    run.chmod(0o700)
    target = run / 'fixture'
    shutil.copytree(imports, target / 'imports')
    consumer = target / 'consumer'
    consumer.mkdir()
    for name in ['Agent.qml', 'Main.qml', 'Panel.qml']:
        source = ROOT / name
        if source.is_symlink():
            raise ValueError('Consumer symlink is not allowed')
        shutil.copy2(source, consumer / name)
    if any(p.is_symlink() for p in (ROOT / 'assets').rglob('*')):
        raise ValueError('Asset symlink is not allowed')
    shutil.copytree(ROOT / 'assets', consumer / 'assets')
    images = run / 'images'
    images.mkdir()
    template = (FIXTURE / 'tst_panel.qml').read_text()
    if template.count('@OUTPUT_DIR@') != 1:
        raise ValueError('Expected one output-directory placeholder')
    quoted = json.dumps(str(images))[1:-1]
    (target / 'tst_panel.qml').write_text(template.replace('@OUTPUT_DIR@', quoted))
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-parent', type=Path,
                        default=Path(tempfile.gettempdir()) / 'slovn-agents-tests')
    parser.add_argument('--qmltestrunner', type=Path, default=Path('/usr/lib/qt6/bin/qmltestrunner'))
    parser.add_argument('--known-bug', action='store_true',
                        help='Run only the missing-icon-to-Pi regression (legacy option name)')
    args = parser.parse_args()
    if not args.qmltestrunner.is_file() or not os.access(args.qmltestrunner, os.X_OK):
        parser.error('Qt Quick Test runner unavailable; supply its explicit executable path')
    run = prepare(args.output_parent)
    home = run / 'home'
    home.mkdir()
    runtime = run / 'runtime'
    runtime.mkdir(mode=0o700)
    env = {
        'PATH': '/usr/bin:/bin', 'HOME': str(home), 'XDG_RUNTIME_DIR': str(runtime),
        'XDG_CONFIG_HOME': str(home / 'config'), 'XDG_CACHE_HOME': str(home / 'cache'),
        'XDG_STATE_HOME': str(home / 'state'), 'QT_QPA_PLATFORM': 'offscreen',
        'QT_QUICK_BACKEND': 'software', 'QSG_RHI_BACKEND': 'software',
        'QT_SCALE_FACTOR': '1', 'QML_IMPORT_PATH': '', 'LC_ALL': 'C.UTF-8',
    }
    tests = ['test_missing_icon_then_pi'] if args.known_bug else DEFAULT_TESTS
    command = [str(args.qmltestrunner.resolve()), '-input', str(run / 'fixture/tst_panel.qml'),
               '-import', str(run / 'fixture/imports'), '-o', '-,txt']
    command += ['PiDailyCachePanel::' + name for name in tests]
    try:
        result = subprocess.run(command, cwd=run, env=env, capture_output=True, text=True, timeout=30)
        code, output = result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired as error:
        code = 124
        output = (error.stdout or b'').decode(errors='replace') + (error.stderr or b'').decode(errors='replace')
    (run / 'test.log').write_text(output)
    record = {
        'command': command, 'environment': env, 'exit': code,
        'scenario': 'icon-regression' if args.known_bug else 'default-contracts',
        'source_hashes': {name: digest(run / 'fixture/consumer' / name)
                          for name in ['Agent.qml', 'Main.qml', 'Panel.qml']},
        'fixture_hashes': {str(p.relative_to(run / 'fixture')): digest(p)
                           for p in sorted((run / 'fixture').rglob('*')) if p.is_file()},
        'geometry': [440, 720], 'panel_width': 380, 'DPR': 1,
        'limitations': ['KeyboardPanel adapted to Item', 'inert Process, FileView and IPC',
                        'no host Bar.qml overlay or compositor input', 'not qml-preview acceptance',
                        'no collector, network, real usage record or production state'],
    }
    (run / 'run.json').write_text(json.dumps(record, indent=2) + '\n')
    print(output, end='')
    print('Evidence:', run)
    return code


if __name__ == '__main__':
    sys.exit(main())
