#!/usr/bin/env python3
"""Catch packed gateway's hidden ELF dependencies that ldd cannot inspect."""
import json
import os
from pathlib import Path
import resource
import subprocess
import tempfile

resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
with tempfile.TemporaryDirectory() as work:
    result = subprocess.run(
        ['/opt/dnf/ubuntu/run-game', '/home/template/root/DnfGateServer'],
        cwd=work, env=dict(os.environ, LD_BIND_NOW='1'), timeout=10,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    output = result.stdout
    # The known unconfigured application exception proves control passed the loader.
    ok = 'invalid ini file:Config.ini' in output and 'error while loading' not in output
    report = {'probe': 'packed gateway eager binding, intentionally absent Config.ini',
              'exit_code': result.returncode, 'output': output, 'passed': ok}
    Path('/opt/dnf/audit/gate-start-proof.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
    raise SystemExit(0 if ok else 1)
