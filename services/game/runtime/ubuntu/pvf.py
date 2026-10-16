"""Require an operator-supplied PVF before any database initialization."""
import os
from pathlib import Path
import sys


def validate(role, path=Path('/data/Script.pvf')):
    if role not in ('ALL', 'GAME'):
        return
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0 or not os.access(path, os.R_OK):
        raise ValueError('Supply a readable, non-empty Script.pvf at /data/Script.pvf '
                         '(host: runtime/game/data/Script.pvf) before starting ALL/GAME.')


if __name__ == '__main__':
    try:
        validate(os.environ.get('SERVER_TYPE'))
    except (ValueError, OSError) as exc:
        print('Ubuntu PVF: ' + str(exc), file=sys.stderr)
        sys.exit(1)
