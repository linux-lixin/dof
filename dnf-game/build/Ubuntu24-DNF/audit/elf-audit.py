#!/usr/bin/env python3
"""Audit trusted, locally supplied game ELFs inside the target Linux image.

ldd executes the system loader: never use this on untrusted uploaded files.
Reports static requirements and resolved relocations; gameplay needs separate tests.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def run(*args, env=None):
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, env=env)
    return result.stdout.strip()


def audit(root, compat, extra=()):
    records = []
    for path in sorted(set(root.rglob('*')) | set(extra)):
        if not path.is_file():
            continue
        with path.open('rb') as stream:
            head = stream.read(20)
        if head[:4] != b'\x7fELF':
            continue
        arch = 'i386' if head[4] == 1 else 'amd64'
        program = run('readelf', '-lW', str(path))
        dynamic = run('readelf', '-dW', str(path))
        versions = run('readelf', '--version-info', '-W', str(path))
        interp = re.search(r'Requesting program interpreter: (.*?)\]', program)
        env = dict(os.environ, LD_LIBRARY_PATH=f'{compat}/{arch}')
        linkage = run('ldd', '-r', str(path), env=env)
        errors = [line.strip() for line in linkage.splitlines()
                  if re.search(r'not found|undefined symbol|error while loading', line)]
        records.append(dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            architecture=arch, interpreter=interp.group(1) if interp else None,
                            needed=re.findall(r'Shared library: \[(.*?)\]', dynamic),
                            symbol_versions=sorted(set(re.findall(r'(?:GLIBCXX|GLIBC|CXXABI|GCC)_[\d.]+', versions))),
                            resolution=linkage, errors=errors))
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--compat', default='/opt/dnf/compat')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--extra', type=Path, action='append', default=[])
    args = parser.parse_args()
    records = audit(args.root, args.compat, args.extra)
    args.output.write_text(json.dumps(records, indent=2) + '\n')
    bad = [r for r in records if r['errors']]
    print(f'{len(records)} ELF files; {len(bad)} unresolved')
    for record in bad:
        print(record['path'], *record['errors'], sep='\n  ')
    raise SystemExit(bool(bad))
