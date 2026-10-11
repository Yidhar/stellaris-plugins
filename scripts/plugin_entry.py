"""Makes the plugins.jsonl line of a plugin from a release on GitHub: downloads its zip, reads the stl-plugin.json in it, and works out the
SHA-256. For authors: put the line it prints into plugins.jsonl (replacing the old one of the same id) and open a pull request.

    python scripts/plugin_entry.py <owner/repo> [--tag v1.2.0] [--asset 'my-plugin-*.zip'] [--author NAME] [--tags a,b] [--game-version 4.5.2]

The release must have one zip holding stl-plugin.json and the DLL (at its root or in one folder). Only the Python standard library is needed;
set GITHUB_TOKEN to avoid the API's limit for anonymous use.
"""
import argparse
import datetime
import fnmatch
import hashlib
import io
import json
import os
import sys
import urllib.request
import zipfile

MANIFEST = 'stl-plugin.json'


def get(url, accept=None):
    req = urllib.request.Request(url, headers={'User-Agent': 'stellaris-plugins-index'})
    if accept:
        req.add_header('Accept', accept)
    token = os.environ.get('GITHUB_TOKEN')
    if token and url.startswith('https://api.github.com/'):
        req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def manifest_in(zip_bytes):
    """The stl-plugin.json of a plugin zip (at its root or in one folder), and the names in the zip."""
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = z.namelist()
    for name in names:
        parts = name.replace('\\', '/').split('/')
        if parts[-1] == MANIFEST and len(parts) <= 2:
            prefix = '/'.join(parts[:-1])
            return json.loads(z.read(name).decode('utf-8-sig')), prefix, names
    raise ValueError(f'the zip holds no {MANIFEST} at its root or in one folder')


def entry(repo, tag=None, asset=None, author=None, tags=None, game_version=None):
    api = f'https://api.github.com/repos/{repo}'
    info = json.loads(get(api))
    rel = json.loads(get(f'{api}/releases/tags/{tag}' if tag else f'{api}/releases/latest'))
    zips = [a for a in rel['assets'] if a['name'].lower().endswith('.zip') and (not asset or fnmatch.fnmatch(a['name'], asset))]
    if len(zips) != 1:
        names = ', '.join(a['name'] for a in rel['assets'])
        raise SystemExit(f'release {rel["tag_name"]} of {repo} has {len(zips)} zips matching {asset or "*.zip"} (assets: {names}); pass --asset')
    url = zips[0]['browser_download_url']
    data = get(url)
    m, _, _ = manifest_in(data)
    e = {
        'id': m['id'],
        'name': m['name'],
        'author': author or info['owner']['login'],
        'description': m.get('description') or info.get('description') or '',
        'version': m.get('version') or rel['tag_name'].lstrip('v'),
        'download': url,
        'sha256': hashlib.sha256(data).hexdigest(),
        'repository': info['html_url'],
    }
    builds = (m.get('game') or {}).get('exe_timestamps') or []
    if builds:
        e['game_builds'] = builds
    if game_version:
        e['game_version'] = game_version
    if tags:
        e['tags'] = tags
    if m.get('homepage') and m['homepage'] != info['html_url']:
        e['homepage'] = m['homepage']
    spdx = (info.get('license') or {}).get('spdx_id')
    if spdx and spdx != 'NOASSERTION':
        e['license'] = spdx
    e['updated'] = datetime.date.today().isoformat()
    return e


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('repo', help='owner/repo on GitHub')
    ap.add_argument('--tag')
    ap.add_argument('--asset', help="the zip's name, * as a wildcard, when the release has more than one")
    ap.add_argument('--author')
    ap.add_argument('--tags', help='comma-separated, lower case')
    ap.add_argument('--game-version')
    a = ap.parse_args()
    tags = [t.strip() for t in a.tags.split(',') if t.strip()] if a.tags else None
    line = json.dumps(entry(a.repo, a.tag, a.asset, a.author, tags, a.game_version), ensure_ascii=False, separators=(',', ':'))
    sys.stdout.buffer.write((line + '\n').encode('utf-8'))
