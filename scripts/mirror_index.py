"""Copies the plugins of plugins.jsonl to the launcher's mirror (the Cloudflare R2 bucket stellaris-plugins, served at
https://plugins.stellarismod.com/) and
publishes the mirror's index, signed. Run by the `update` workflow after plugins.jsonl is built.

    python scripts/mirror_index.py [--dry-run] [--key private.pem]

1. Each plugin's zip is downloaded from its GitHub release, checked against the SHA-256 in plugins.jsonl, and uploaded to
   <id>/v<version>/<file> once (a copy already there is left alone: those paths never change).
2. index.json is {"manifest": <the index as JSON text>, "signature": <Ed25519, hex>}. In the manifest each plugin's `download` is
   its copy on the mirror and `fallback` the GitHub asset; the launcher reads it only when the signature verifies with the public key built
   into it, and takes a zip from either place only when it matches the SHA-256. So whoever can write to the bucket cannot change what is
   installed. It is uploaded last, and only when it changed.

Needs CLOUDFLARE_ACCOUNT_ID, the private key (PLUGIN_INDEX_SIGNING_KEY, the PEM text, or --key), and a way to write: in CI,
R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY, the S3 credentials of a token that may write only this bucket's objects (the token's id, and the
SHA-256 of its value); on a maintainer's machine, CLOUDFLARE_API_TOKEN for wrangler. Without them it says so and does nothing, so the
workflow keeps working before they are set.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / 'plugins.jsonl'
BUCKET = 'stellaris-plugins'  # its own bucket: the CI's token cannot touch the launcher's files
PUBLIC = 'https://plugins.stellarismod.com'
PRODUCT = 'stellaris-plugins'
UA = 'stellaris-plugins-mirror'  # Cloudflare turns away Python's default User-Agent
IMMUTABLE = 'public, max-age=31536000, immutable'
SHORT = 'public, max-age=300'


def http(url, method='GET'):
    req = urllib.request.Request(url, method=method, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b''


def s3_keys():
    return os.environ.get('R2_ACCESS_KEY_ID'), os.environ.get('R2_SECRET_ACCESS_KEY')


def put(local, key, content_type, cache):
    access, secret = s3_keys()
    if access and secret:
        # CI: S3 credentials of a token that may write only this bucket's objects (the Cloudflare API, which wrangler uses, does not
        # take a token scoped that narrowly)
        import boto3
        s3 = boto3.client('s3', endpoint_url=f'https://{os.environ["CLOUDFLARE_ACCOUNT_ID"]}.r2.cloudflarestorage.com',
                          aws_access_key_id=access, aws_secret_access_key=secret, region_name='auto')
        s3.upload_file(str(local), BUCKET, key, ExtraArgs={'ContentType': content_type, 'CacheControl': cache})
        return
    exe = shutil.which('wrangler')
    cmd = [exe] if exe else [shutil.which('npx') or 'npx', '--yes', 'wrangler@4.85.0']
    subprocess.run([*cmd, 'r2', 'object', 'put', f'{BUCKET}/{key}', '--file', str(local), '--remote', '--content-type', content_type,
                    '--cache-control', cache], check=True, stdout=subprocess.DEVNULL)


def load_key(path):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    pem = Path(path).read_bytes() if path else os.environ.get('PLUGIN_INDEX_SIGNING_KEY', '').encode()
    if not pem.strip():
        return None
    key = serialization.load_pem_private_key(pem, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        sys.exit('the signing key is not an Ed25519 key')
    return key


def safe(part):
    return part and part not in ('.', '..') and all(c.isalnum() or c in '-_.' for c in part)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='check and sign, upload nothing')
    ap.add_argument('--key', default=None, help='the private key file (default: PLUGIN_INDEX_SIGNING_KEY)')
    a = ap.parse_args()
    key = load_key(a.key)
    write = ('R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY') if any(s3_keys()) else ('CLOUDFLARE_API_TOKEN',)
    missing = [n for n in (*write, 'CLOUDFLARE_ACCOUNT_ID') if not os.environ.get(n)]
    if key is None or (missing and not a.dry_run):
        print(f'the mirror is not set up here (missing: {", ".join(missing + ([] if key else ["PLUGIN_INDEX_SIGNING_KEY"]))}); nothing done')
        return

    entries = [json.loads(l) for l in INDEX.read_text(encoding='utf-8').splitlines() if l.strip()]
    mirrored = []
    with tempfile.TemporaryDirectory(prefix='stl-plugins-mirror-') as tmp:
        tmp = Path(tmp)
        for e in entries:
            name = e['download'].rsplit('/', 1)[-1]
            parts = (e['id'], 'v' + e['version'], name)
            if not all(safe(p) for p in parts) or not e['download'].startswith('https://'):
                print(f'problem: {e["id"]}: cannot be mirrored ({"/".join(parts)})')
                continue
            path = '/'.join(parts)
            url = f'{PUBLIC}/{path}'
            status, _ = http(url, 'HEAD')
            if status == 200:
                print(f'{e["id"]} {e["version"]}: already on the mirror')
            else:
                status, data = http(e['download'])
                got = hashlib.sha256(data).hexdigest()
                if status != 200 or got != e['sha256'].lower():
                    print(f'problem: {e["id"]}: {e["download"]} gave {status}, SHA-256 {got} (index: {e["sha256"]}); not mirrored')
                    continue
                if a.dry_run:
                    print(f'{e["id"]} {e["version"]}: would upload {url}')
                else:
                    f = tmp / name
                    f.write_bytes(data)
                    put(f, path, 'application/zip', IMMUTABLE)
                    print(f'{e["id"]} {e["version"]}: uploaded {url}')
            mirrored.append({**e, 'download': url, 'fallback': e['download']})

        manifest = json.dumps({'product': PRODUCT, 'plugins': mirrored}, ensure_ascii=False, separators=(',', ':'))
        status, body = http(f'{PUBLIC}/index.json')
        try:
            current = json.loads(body)['manifest'] if status == 200 else None
        except (ValueError, KeyError):
            current = None
        if current == manifest:
            print('index.json unchanged')
            return
        signature = key.sign(manifest.encode('utf-8')).hex()
        key.public_key().verify(bytes.fromhex(signature), manifest.encode('utf-8'))
        if a.dry_run:
            print(f'index.json would change ({len(mirrored)} plugin(s))')
            return
        f = tmp / 'index.json'
        f.write_text(json.dumps({'manifest': manifest, 'signature': signature}, ensure_ascii=False), encoding='utf-8')
        put(f, 'index.json', 'application/json; charset=utf-8', SHORT)
        print(f'index.json updated ({len(mirrored)} plugin(s))')


if __name__ == '__main__':
    main()
