"""Emit one startup-complete message after role health and fresh channel logs pass."""
import os
from pathlib import Path
import re
import subprocess
import sys
import time

COUNTRIES={'CN','HK','KR','MO','TW'}
PATTERN=re.compile(rb'GeoIP Allow Country Code\s*:\s*(CN|HK|KR|MO|TW)\b')


def channel_names(env):
    if env.get('SERVER_TYPE','ALL') not in ('ALL','GAME'):
        return []
    group=('cain','diregie','siroco','prey','casillas','hilder')[int(env.get('SERVER_GROUP','3'))-1]
    return [group+f'{int(number):02d}' for number in env.get('OPEN_CHANNEL','11,52').split(',')]


def check_countries(root,env):
    for name in channel_names(env):
        seen=set()
        for path in (Path(root)/name).glob('Log*.init'):
            if path.is_symlink() or not path.is_file():
                continue
            try:
                with path.open('rb') as stream:
                    for line in stream:
                        match=PATTERN.search(line)
                        if match: seen.add(match[1].decode('ascii'))
            except FileNotFoundError:
                continue
        if seen!=COUNTRIES:
            raise ValueError('channel '+name+' current initialization incomplete')


def output(message):
    print(message,flush=True)


def wait_ready(check,message,timeout=600,emit=output):
    deadline=time.monotonic()+timeout
    consecutive=0
    reason='readiness checks not yet stable'
    while time.monotonic()<deadline:
        try:
            check()
            consecutive+=1
            if consecutive==3:
                emit(message)
                return 0
            reason='readiness checks not yet stable'
        except (ValueError,OSError,KeyError,subprocess.TimeoutExpired) as exc:
            consecutive=0
            reason=str(exc)
        time.sleep(2)
    emit(f'[启动未完成] 等待 {timeout} 秒超时：{reason}')
    return 1


def main():
    import health
    def check():
        health.check()
        check_countries('/home/neople/game/log',os.environ)
    role=os.environ.get('SERVER_TYPE','ALL')
    names=channel_names(os.environ)
    detail=role+('；频道：'+'、'.join(names) if names else '')
    message=f'[启动完成] 游戏服务已全部就绪（{detail}）'
    return wait_ready(check,message,int(os.environ.get('STARTUP_TIMEOUT','600')))


if __name__=='__main__':
    sys.exit(main())
