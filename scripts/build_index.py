"""Builds plugins.jsonl from sources.jsonl: for each repository there, the latest release's zip — downloaded, its stl-plugin.json read and
checked, its SHA-256 worked out. Run by the `update` workflow every hour, so a new release shows in the index without anyone editing it.

    python scripts/build_index.py [--check]

A repository whose latest release cannot be used keeps its earlier line (and is reported); one that never had a usable release is left out.
--check writes nothing and fails when a repository has no usable release (for pull requests adding one).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plugin_entry import entry, line, repo_of  # noqa: E402
from check_index import check_fields, check_bytes  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(ROOT, 'sources.jsonl')
INDEX = os.path.join(ROOT, 'plugins.jsonl')
SOURCE_FIELDS = {'repository', 'asset', 'tags', 'author'}


def read_sources():
    """The lines of sources.jsonl, and what is wrong with them."""
    out, errors, seen = [], [], set()
    with open(SOURCES, encoding='utf-8') as f:
        for n, raw in enumerate(f, 1):
            if not raw.strip():
                continue
            try:
                s = json.loads(raw)
                repo = repo_of(s['repository'])
            except Exception as x:  # noqa: BLE001
                errors.append(f'sources.jsonl line {n}: {x}')
                continue
            extra = set(s) - SOURCE_FIELDS
            if extra:
                errors.append(f'sources.jsonl line {n}: unknown field(s) {sorted(extra)}')
            if repo.lower() in seen:
                errors.append(f'sources.jsonl line {n}: {repo} is on an earlier line too')
            seen.add(repo.lower())
            out.append((repo, s))
    return out, errors


def main():
    check_only = '--check' in sys.argv
    sources, errors = read_sources()
    old = {}
    if os.path.exists(INDEX):
        with open(INDEX, encoding='utf-8') as f:
            for raw in f:
                if raw.strip():
                    e = json.loads(raw)
                    old[repo_of(e['repository']).lower()] = e
    lines, problems, ids = [], [], set()
    for repo, s in sources:
        try:
            e, data = entry(repo, asset=s.get('asset'), author=s.get('author'), tags=s.get('tags'))
            bad = check_fields(e) + check_bytes(e, data)
            if bad:
                raise ValueError('; '.join(bad))
        except Exception as x:  # noqa: BLE001
            kept = old.get(repo.lower())
            problems.append(f'{repo}: {x}' + (' (its earlier line is kept)' if kept else ' (left out)'))
            if not kept:
                continue
            e = kept
        if e['id'] in ids:
            problems.append(f'{repo}: the id {e["id"]!r} is another repository\'s too (left out)')
            continue
        ids.add(e['id'])
        lines.append(line(e))
        print(f'{e["id"]} {e["version"]}  {repo}')
    for x in errors + problems:
        print(f'problem: {x}')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as f:
            f.write(f'{len(lines)} plugin(s)\n\n' + ''.join(f'- {x}\n' for x in errors + problems))
    if check_only:
        sys.exit(1 if errors or problems else 0)
    if errors:
        sys.exit(1)
    text = ''.join(l + '\n' for l in lines)
    if not os.path.exists(INDEX) or open(INDEX, encoding='utf-8').read() != text:
        with open(INDEX, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        print('plugins.jsonl changed')
    else:
        print('plugins.jsonl unchanged')


if __name__ == '__main__':
    main()
