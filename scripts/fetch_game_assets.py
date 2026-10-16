#!/usr/bin/env python3
"""Restore ignored, pinned upstream runtime inputs; never overwrite custom files."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import urllib.parse
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[1]
LOCK=Path(__file__).with_name('game-assets.lock.json')

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def restore(asset,args):
    relative=Path(asset['path'])
    target=(ROOT/relative).resolve()
    target.relative_to((ROOT/'dnf-game').resolve())
    expected=asset['sha256']
    if target.exists() and not args.check_remote:
        if target.stat().st_size==asset['bytes'] and digest(target)==expected:
            return 'OK '+asset['path']
        raise RuntimeError('Existing file differs from upstream; preserve/move it before fetching: '+asset['path'])
    if args.verify:
        raise RuntimeError('Missing asset: '+asset['path'])
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_name('.download-'+uuid.uuid4().hex)
    try:
        if args.cache_dir and not args.check_remote:
            cached=Path(args.cache_dir)/relative
        else:
            cached=None
        if cached and cached.is_file() and digest(cached)==expected:
            shutil.copyfile(cached,temporary)
        else:
            parsed=urllib.parse.urlsplit(asset['url'])
            if parsed.scheme!='https' or parsed.hostname!='raw.githubusercontent.com':
                raise RuntimeError('Unexpected asset host')
            url=urllib.parse.urlunsplit(parsed._replace(path=urllib.parse.quote(parsed.path,safe='/')))
            with urllib.request.urlopen(url,timeout=120) as response,temporary.open('xb') as out:
                shutil.copyfileobj(response,out)
        if temporary.stat().st_size!=asset['bytes'] or digest(temporary)!=expected:
            raise RuntimeError('Downloaded size/SHA256 mismatch: '+asset['path'])
        if not args.check_remote:
            temporary.replace(target)
            # Git stores executable bits, but Windows copies do not. Runtime entry
            # scripts chmod most binaries; restore original executable inputs too.
            if asset.get('executable'):target.chmod(target.stat().st_mode|0o111)
        return ('REMOTE VERIFIED ' if args.check_remote else 'RESTORED ')+asset['path']
    finally:
        temporary.unlink(missing_ok=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true',help='Verify local inputs without downloading')
    parser.add_argument('--check-remote',action='store_true',help='Download/hash upstream without changing local inputs')
    parser.add_argument('--only',help='One exact path from the lock file')
    parser.add_argument('--cache-dir',help='Optional existing workspace root containing dnf-game/')
    args=parser.parse_args()
    if args.verify and args.check_remote:parser.error('Choose --verify or --check-remote')
    assets=json.loads(LOCK.read_text(encoding='utf8'))['assets']
    if args.only:
        assets=[a for a in assets if a['path']==args.only]
        if not assets:parser.error('Path is not in the asset lock')
    with ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(lambda a:restore(a,args),assets):print(result,flush=True)
    print('Verified',len(assets),'upstream runtime inputs.')

if __name__=='__main__':main()
