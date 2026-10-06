#!/usr/bin/env python3
"""Prepare stable Agents updates with Git three-way merge; publish only tested patches."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'omacom/omarchy'
PREFIX = 'shell/plugins/agents/'
LIMIT = 2 * 1024 * 1024


def git(root, *args, check=True):
    return subprocess.run(['git', '-C', str(root), *args], check=check,
                          capture_output=True, text=True, timeout=60)


def allowed(path):
    return path in {'Agent.qml', 'Main.qml', 'Panel.qml', 'README.md', 'manifest.json'} or bool(
        re.fullmatch(r'assets/[a-z0-9_-]+\.svg', path))


def validate(files):
    if len(files) > 100 or sum(map(len, files.values())) > LIMIT:
        raise ValueError('Upstream subtree size limit exceeded')
    for name, data in files.items():
        if not allowed(name) or not isinstance(data, bytes) or len(data) > LIMIT:
            raise ValueError('Unsupported upstream path/content: ' + name)
    required = {'Agent.qml', 'Main.qml', 'Panel.qml', 'README.md', 'manifest.json'}
    if not required <= files.keys():
        raise ValueError('Required upstream files missing')
    manifest = json.loads(files['manifest.json'])
    if manifest['schemaVersion'] != 1 or manifest['id'] != 'omarchy.agents':
        raise ValueError('Unsupported upstream manifest')
    if manifest['entryPoints'] != {'barWidget': 'Panel.qml'}:
        raise ValueError('Upstream entry-point contract changed')


def read_files(root):
    if root.is_symlink():
        raise ValueError('Snapshot root symlink')
    files = {}
    for path in root.rglob('*'):
        if path.is_symlink():
            raise ValueError('Snapshot symlink')
        if path.is_file():
            files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files


def hashes(files):
    return {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}


def api(path):
    if not path.startswith('/repos/' + REPOSITORY + '/'):
        raise ValueError('Unexpected upstream endpoint')
    request = urllib.request.Request('https://api.github.com' + path,
                                    headers={'Accept': 'application/vnd.github+json',
                                             'User-Agent': 'omarchy-agents-pi-stable-updater'})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError('GitHub API response too large')
    return json.loads(data)


def fetch_stable():
    release = api('/repos/' + REPOSITORY + '/releases/latest')
    tag = release['tag_name']
    if release['draft'] or release['prerelease'] or not re.fullmatch(r'v\d+\.\d+\.\d+', tag):
        raise ValueError('Not a numbered stable release')
    obj = api('/repos/' + REPOSITORY + '/git/ref/tags/' + tag)['object']
    if obj['type'] == 'tag':
        obj = api('/repos/' + REPOSITORY + '/git/tags/' + obj['sha'])['object']
    if obj['type'] != 'commit' or not re.fullmatch(r'[0-9a-f]{40}', obj['sha']):
        raise ValueError('Invalid stable commit')
    commit = obj['sha']
    files = {}
    total = 0
    def walk(path):
        nonlocal total
        entries = api('/repos/' + REPOSITORY + '/contents/' + PREFIX + path + '?ref=' + commit)
        if not isinstance(entries, list) or len(entries) > 100:
            raise ValueError('Invalid upstream directory')
        for entry in entries:
            name = entry['path'].removeprefix(PREFIX)
            if entry['path'] != PREFIX + name:
                raise ValueError('Invalid upstream prefix')
            if entry['type'] == 'dir' and name == 'assets' and path == '':
                walk('assets')
            elif entry['type'] == 'file' and allowed(name):
                if entry['size'] > LIMIT or len(files) >= 100:
                    raise ValueError('Upstream file count/size exceeded')
                blob = api('/repos/' + REPOSITORY + '/contents/' + PREFIX + name + '?ref=' + commit)
                if blob['type'] != 'file' or blob.get('encoding') != 'base64':
                    raise ValueError('Unsupported upstream file')
                content = base64.b64decode(blob['content'], validate=False)
                total += len(content)
                if total > LIMIT:
                    raise ValueError('Upstream subtree too large')
                files[name] = content
            else:
                raise ValueError('Unsupported upstream entry: ' + name)
    walk('')
    validate(files)
    return {'repository': REPOSITORY, 'tag': tag, 'commit': commit, 'files': hashes(files)}, files


def merge(base, ours, theirs):
    """Use Git's native ancestry-aware merge, including additions and deletions."""
    validate(base)
    validate(theirs)
    if any(not allowed(name) for name in ours):
        raise ValueError('Unsupported local plugin path')
    with tempfile.TemporaryDirectory(prefix='agents-merge-') as scratch:
        root = Path(scratch)
        git(root, 'init', '-q', '-b', 'base')
        git(root, 'config', 'user.name', 'Agents update test')
        git(root, 'config', 'user.email', 'agents-update@users.noreply.github.com')
        def snapshot(files):
            for path in root.iterdir():
                if path.name == '.git':
                    continue
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            for name, data in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            git(root, 'add', '--all')
            git(root, 'commit', '-q', '--allow-empty', '-m', 'Plugin snapshot')
        snapshot(base)
        git(root, 'checkout', '-q', '-b', 'ours')
        snapshot(ours)
        git(root, 'checkout', '-q', '-b', 'theirs', 'base')
        snapshot(theirs)
        git(root, 'checkout', '-q', 'ours')
        result = git(root, 'merge', '--no-edit', 'theirs', check=False)
        if result.returncode:
            conflicts = git(root, 'diff', '--name-only', '--diff-filter=U').stdout.strip()
            raise ValueError('Upstream merge failed; checkout unchanged: ' + conflicts)
        return {name: (root / name).read_bytes()
                for name in git(root, 'ls-files').stdout.splitlines()}


def prepare(patch):
    if git(ROOT, 'status', '--porcelain').stdout.strip():
        raise ValueError('Update requires a clean source checkout')
    base_meta = json.loads((ROOT / '.upstream/base.json').read_text())
    base = read_files(ROOT / '.upstream/agents')
    validate(base)
    if base_meta['repository'] != REPOSITORY or hashes(base) != base_meta['files']:
        raise ValueError('Upstream baseline mismatch')
    meta, theirs = fetch_stable()
    if meta['tag'] == base_meta['tag']:
        if meta != base_meta:
            raise ValueError('Stable tag changed; manual review required')
        print('Already tracking latest stable release: ' + meta['tag'])
        return
    version = lambda tag: tuple(map(int, tag[1:].split('.')))
    if version(meta['tag']) <= version(base_meta['tag']):
        raise ValueError('Upstream release downgrade refused')
    ours = {name: (ROOT / name).read_bytes() for name in git(ROOT, 'ls-files').stdout.splitlines()
            if allowed(name)}
    combined = merge(base, ours, theirs)
    # All remote parsing and merging finish before any source checkout mutation.
    for name in ours.keys() - combined.keys():
        (ROOT / name).unlink()
    for name, data in combined.items():
        path = ROOT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    shutil.rmtree(ROOT / '.upstream/agents')
    for name, data in theirs.items():
        path = ROOT / '.upstream/agents' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (ROOT / '.upstream/base.json').write_text(json.dumps(meta, indent=2) + '\n')
    git(ROOT, 'add', '--', '.upstream', *sorted(ours.keys() | combined.keys()))
    patch.write_text(git(ROOT, 'diff', '--cached', '--binary').stdout)
    print('Prepared ' + meta['tag'] + '; tests required before publication')


def publish(patch, repository):
    if repository != 'PavelLizunov/omarchy-agents-pi':
        raise ValueError('Unexpected publication repository')
    if git(ROOT, 'status', '--porcelain').stdout.strip():
        raise ValueError('Publication checkout must be clean')
    if patch.is_symlink() or not patch.is_file() or not 0 < patch.stat().st_size <= 4 * LIMIT:
        raise ValueError('Invalid update patch file/size')
    stats = git(ROOT, 'apply', '--numstat', '-z', str(patch)).stdout.split('\0')
    for entry in filter(None, stats):
        name = entry.split('\t', 2)[-1]
        stock = name.removeprefix('.upstream/agents/')
        if not (allowed(name) or (name.startswith('.upstream/agents/') and allowed(stock))
                or name == '.upstream/base.json'):
            raise ValueError('Patch modifies forbidden path: ' + name)
    summary = git(ROOT, 'apply', '--summary', str(patch)).stdout
    if '120000' in summary or '160000' in summary or 'rename ' in summary or 'mode change' in summary:
        raise ValueError('Patch changes symlinks, submodules or modes')
    git(ROOT, 'apply', '--check', str(patch))
    git(ROOT, 'apply', '--index', str(patch))
    meta = json.loads((ROOT / '.upstream/base.json').read_text())
    if not re.fullmatch(r'v\d+\.\d+\.\d+', meta['tag']):
        raise ValueError('Invalid update tag')
    stock = read_files(ROOT / '.upstream/agents')
    validate(stock)
    if meta['repository'] != REPOSITORY or hashes(stock) != meta['files']:
        raise ValueError('Invalid update baseline')
    subprocess.run(['python3', '-B', str(ROOT / 'tests/check.py')], check=True, timeout=60)
    branch = 'upstream/' + meta['tag']
    # One outstanding update at a time; never overwrite reviewer work or force-push.
    pending = json.loads(subprocess.check_output(
        ['gh', 'pr', 'list', '--repo', repository, '--state', 'open', '--json', 'headRefName'], text=True))
    if any(pr['headRefName'].startswith('upstream/') for pr in pending):
        raise ValueError('An upstream update PR is already open; review it first')
    if git(ROOT, 'ls-remote', '--heads', 'origin', branch).stdout.strip():
        raise ValueError('Update branch already exists; manual review required')
    git(ROOT, 'checkout', '-b', branch)
    git(ROOT, 'config', 'user.name', 'github-actions[bot]')
    git(ROOT, 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    git(ROOT, 'commit', '-m', 'Update Agents from Omarchy ' + meta['tag'])
    git(ROOT, 'push', 'origin', 'HEAD:refs/heads/' + branch)
    body = ('Three-way merge from stable Omarchy ' + meta['tag'] + ' (`' + meta['commit']
            + '`). Isolated tests passed before this branch was published. '
            'Exact-head CI is dispatched explicitly. Manual review and merge required; '
            'no deployment or automatic merge. Host compositor and collector behavior remain unverified.')
    subprocess.run(['gh', 'pr', 'create', '--repo', repository, '--base', 'main', '--head', branch,
                    '--title', 'Update Agents from Omarchy ' + meta['tag'], '--body', body], check=True)
    subprocess.run(['gh', 'workflow', 'run', 'ci.yml', '--repo', repository, '--ref', branch], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'publish'])
    parser.add_argument('--patch', type=Path, required=True)
    parser.add_argument('--repository', default='PavelLizunov/omarchy-agents-pi')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.patch.resolve())
    else:
        publish(args.patch.resolve(), args.repository)
