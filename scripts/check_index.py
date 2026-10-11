"""Checks plugins.jsonl: every line one JSON object with the fields of schema/plugin-entry.schema.json, ids unique; and for each line, that
its zip downloads, matches its SHA-256, and holds a stl-plugin.json of the same id and version (and builds) with the DLL it names.

    python scripts/check_index.py [plugins.jsonl] [--offline]

--offline checks only the lines themselves (no downloads). Exits non-zero, after saying why, when anything is wrong.
"""
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plugin_entry import get, manifest_in  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = json.load(open(os.path.join(ROOT, 'schema', 'plugin-entry.schema.json'), encoding='utf-8'))


def check_fields(e):
    """What is wrong with a line's fields (the schema's rules, without a JSON-schema library)."""
    errors = []
    props = SCHEMA['properties']
    for k in SCHEMA['required']:
        if k not in e:
            errors.append(f'{k} is missing')
    for k, v in e.items():
        rule = props.get(k)
        if rule is None:
            errors.append(f'{k} is not a known field')
            continue
        if rule['type'] == 'string':
            if not isinstance(v, str):
                errors.append(f'{k} is not text')
                continue
            if 'pattern' in rule and not re.search(rule['pattern'], v):
                errors.append(f'{k} {v!r} does not look right ({rule["pattern"]})')
            if len(v) < rule.get('minLength', 0) or len(v) > rule.get('maxLength', 10 ** 9):
                errors.append(f'{k} is {len(v)} characters (allowed {rule.get("minLength", 0)}-{rule.get("maxLength", "any")})')
        elif rule['type'] == 'array':
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                errors.append(f'{k} is not a list of text')
                continue
            if len(v) > rule.get('maxItems', 10 ** 9):
                errors.append(f'{k} has more than {rule["maxItems"]} items')
            pat = rule.get('items', {}).get('pattern')
            for x in v:
                if pat and not re.search(pat, x):
                    errors.append(f'{k}: {x!r} does not look right ({pat})')
    if isinstance(e.get('download'), str) and isinstance(e.get('repository'), str):
        repo = e['repository'].rstrip('/') + '/releases/download/'
        if not e['download'].startswith(repo):
            errors.append('download is not a release asset of repository')
    return errors


def check_zip(e):
    """What is wrong with a line's zip."""
    return check_bytes(e, get(e['download']))


def check_bytes(e, data):
    """What is wrong with a line's zip, downloaded."""
    got = hashlib.sha256(data).hexdigest()
    if got != e['sha256']:
        return [f'the zip\'s SHA-256 is {got}, not {e["sha256"]}']
    try:
        m, prefix, names = manifest_in(data)
    except Exception as x:  # noqa: BLE001
        return [str(x)]
    errors = []
    if m.get('id') != e['id']:
        errors.append(f'its stl-plugin.json is the plugin {m.get("id")!r}, not {e["id"]!r}')
    if (m.get('version') or '').lstrip('v') != e['version'].lstrip('v'):
        errors.append(f'its stl-plugin.json says version {m.get("version")!r}, not {e["version"]!r}')
    builds = sorted(b.lower() for b in (m.get('game') or {}).get('exe_timestamps') or [])
    if builds != sorted(b.lower() for b in e.get('game_builds', [])):
        errors.append(f'its stl-plugin.json is made for the builds {builds}, the line says {e.get("game_builds", [])}')
    dll = '/'.join(x for x in [prefix, (m.get('dll') or '').replace('\\', '/')] if x)
    if not m.get('dll') or dll not in names:
        errors.append(f'the DLL it names ({m.get("dll")!r}) is not in the zip')
    return errors


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    offline = '--offline' in sys.argv
    path = args[0] if args else os.path.join(ROOT, 'plugins.jsonl')
    bad = 0
    seen = set()
    with open(path, encoding='utf-8') as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError as x:
                print(f'line {n}: not JSON: {x}')
                bad += 1
                continue
            if not isinstance(e, dict):
                print(f'line {n}: not an object')
                bad += 1
                continue
            errors = check_fields(e)
            if e.get('id') in seen:
                errors.append(f'the id {e["id"]!r} is on an earlier line too')
            seen.add(e.get('id'))
            if not errors and not offline:
                try:
                    errors = check_zip(e)
                except Exception as x:  # noqa: BLE001
                    errors = [f'cannot check the zip: {x}']
            name = e.get('id', '?')
            if errors:
                bad += 1
                for x in errors:
                    print(f'line {n} ({name}): {x}')
            else:
                print(f'line {n} ({name}): ok')
    print(f'{len(seen)} plugin(s), {bad} with problems')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
