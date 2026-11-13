"""Adds to sources.jsonl the plugins stellarismod.com lists that it lacks. The site lists a plugin from its GitHub releases once one of its
admins has looked at it, and publishes those repositories as sources.jsonl lines. Run by the `update` workflow before the index is built:

    python scripts/merge_site_sources.py [URL]

Only repositories that are not here yet are added, at the end, so a line edited here stays as it is; nothing is ever removed (a plugin is
taken out by editing sources.jsonl). A line the site sends that this repository would not accept is skipped and reported. When the site
cannot be reached, nothing changes and the run goes on.
"""
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plugin_entry import repo_of  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(ROOT, 'sources.jsonl')
URL = 'https://stellarismod.com/api/v1/plugin-sources.jsonl'
# at most this many new repositories in one run: more than that is a mistake on the site, not a busy hour
MAX_NEW = 20
ASSET = re.compile(r'^[A-Za-z0-9._*-]{1,100}\.zip$', re.I)
TAG = re.compile(r'^[a-z0-9-]{1,24}$')


def site_lines(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'stellaris-plugins-index'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8').splitlines()


def clean(raw):
    """The sources.jsonl line for one line from the site, or why it is refused."""
    s = json.loads(raw)
    if not isinstance(s, dict):
        raise ValueError('not an object')
    repo = repo_of(str(s.get('repository', '')))
    out = {'repository': f'https://github.com/{repo}'}
    asset = s.get('asset')
    if asset is not None:
        if not isinstance(asset, str) or not ASSET.match(asset):
            raise ValueError(f'asset {asset!r}')
        out['asset'] = asset
    tags = s.get('tags') or []
    if not isinstance(tags, list) or len(tags) > 8 or not all(isinstance(t, str) and TAG.match(t) for t in tags):
        raise ValueError(f'tags {tags!r}')
    if tags:
        out['tags'] = tags
    return repo, out


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else URL
    try:
        lines = site_lines(url)
    except Exception as x:  # noqa: BLE001
        print(f'stellarismod.com not reached ({x}); sources.jsonl unchanged')
        return
    have = set()
    with open(SOURCES, encoding='utf-8') as f:
        text = f.read()
    for raw in text.splitlines():
        if raw.strip():
            try:
                have.add(repo_of(json.loads(raw)['repository']).lower())
            except Exception:  # noqa: BLE001
                pass
    new, problems = [], []
    for raw in lines:
        if not raw.strip():
            continue
        try:
            repo, line = clean(raw)
        except Exception as x:  # noqa: BLE001
            problems.append(f'{raw[:120]}: {x}')
            continue
        if repo.lower() in have:
            continue
        have.add(repo.lower())
        new.append(line)
    if len(new) > MAX_NEW:
        print(f'the site lists {len(new)} new repositories, more than {MAX_NEW}: nothing added')
        sys.exit(1)
    for x in problems:
        print(f'skipped: {x}')
    if not new:
        print('no new repositories from stellarismod.com')
        return
    if text and not text.endswith('\n'):
        text += '\n'
    text += ''.join(json.dumps(l, ensure_ascii=False, separators=(',', ':')) + '\n' for l in new)
    with open(SOURCES, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    for l in new:
        print(f'added from stellarismod.com: {l["repository"]}')


if __name__ == '__main__':
    main()
