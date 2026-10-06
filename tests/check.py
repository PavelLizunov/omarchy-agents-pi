#!/usr/bin/env python3
"""Static public-package, upstream snapshot and protected fork contracts."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files'], text=True).splitlines()
    for name in files:
        path = ROOT / name
        if path.is_symlink():
            raise ValueError('Tracked symlink: ' + name)
        data = path.read_bytes()
        if len(data) > 2 * 1024 * 1024:
            raise ValueError('Oversized public file: ' + name)
        if name.endswith('.py'):
            ast.parse(data, filename=name)
        if name.endswith('.json'):
            json.loads(data)
        if name.endswith('.svg'):
            ET.fromstring(data)
        if re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY)', data):
            raise ValueError('Possible credential: ' + name)
    meta = json.loads((ROOT / '.upstream/base.json').read_text())
    if meta['repository'] != 'omacom/omarchy' or not re.fullmatch(r'v\d+\.\d+\.\d+', meta['tag']):
        raise ValueError('Invalid stable baseline')
    if not re.fullmatch(r'[0-9a-f]{40}', meta['commit']):
        raise ValueError('Invalid upstream commit')
    snapshot = ROOT / '.upstream/agents'
    actual = {p.relative_to(snapshot).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in snapshot.rglob('*') if p.is_file()}
    if actual != meta['files']:
        raise ValueError('Upstream snapshot hash mismatch')
    for name in ['Agent.qml', 'assets/claude.svg', 'assets/codex.svg',
                 'assets/codex-light.svg', 'assets/fireworks.svg']:
        if (ROOT / name).read_bytes() != (snapshot / name).read_bytes():
            raise ValueError('Protected upstream file drift: ' + name)
    readme = (ROOT / 'README.md').read_bytes()
    stock_readme = (snapshot / 'README.md').read_bytes()
    if not stock_readme.startswith(b'# Agents\n\n'):
        raise ValueError('Upstream README heading changed; manual review required')
    if not readme.endswith(stock_readme.split(b'\n\n', 1)[1]):
        raise ValueError('Inherited README guide drift')
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    if manifest['id'] != 'slovn.agents' or manifest['omarchy']['clonedFrom'] != 'omarchy.agents':
        raise ValueError('Clone identity changed')
    if manifest['entryPoints'] != {'barWidget': 'Panel.qml'}:
        raise ValueError('Clone entry-point changed')
    panel = (ROOT / 'Panel.qml').read_text()
    main_qml = (ROOT / 'Main.qml').read_text()
    if not (ROOT / 'assets/pi.svg').is_file() or 'cacheRead' not in panel or '"pi"' not in main_qml:
        raise ValueError('Pi preservation contract absent')
    if 'failedSource' not in panel or 'heroMarkImage.status === Image.Error' not in panel:
        raise ValueError('Stale image fallback guard absent')
    if 'Copyright (c) David Heinemeier Hansson' not in (ROOT / 'LICENSE').read_text():
        raise ValueError('Upstream copyright missing')
    print('Static package, provenance and protected fork contracts passed')


if __name__ == '__main__':
    main()
