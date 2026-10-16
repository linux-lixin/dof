"""Verify actual df_game_r PIDs and both listening ports, beyond supervisor wrappers."""
import json
from pathlib import Path
import subprocess
import time

DIST=Path(__file__).resolve().parents[1]/'dist'
state=json.loads((DIST/'image-test-state.json').read_text(encoding='utf8'))
game=state['game']

def cmd(*args):
    r=subprocess.run(['docker','exec',game,*args],capture_output=True,text=True,encoding='utf8',errors='replace')
    return r.stdout

def snapshot():
    pids=cmd('pgrep','-x','df_game_r').split()
    sockets=cmd('cat','/proc/net/tcp')
    listening={int(line.split()[1].split(':')[1],16) for line in sockets.splitlines()[1:] if line.split()[3]=='0A'}
    if len(pids)==2 and {30011,30052}.issubset(listening):
        return sorted(pids)
    return None

result={'started_at':time.strftime('%Y-%m-%d %H:%M:%S'),'status':'running'}
try:
    deadline=time.monotonic()+600
    while time.monotonic()<deadline:
        pids=snapshot()
        if pids: break
        time.sleep(5)
    else: raise RuntimeError('Actual game processes and TCP 30011/30052 were not ready within 10 minutes')
    print('Actual game ready, PIDs:',pids,flush=True)
    result['pids']=pids
    result['ready_at']=time.strftime('%Y-%m-%d %H:%M:%S')
    for i in range(30):
        time.sleep(10)
        assert snapshot()==pids,'Actual game PID or listening port changed'
        if i%6==5: print('Actual game processes and both listening ports stable:',(i+1)*10,'seconds',flush=True)
    result['status']='passed'
    result['stable_seconds']=300
    result['processes']=cmd('ps','-eo','pid,etime,comm')
    result['listening_ports']=cmd('cat','/proc/net/tcp')
    result['game_log_files']=cmd('find','/home/neople/game/log','-type','f')
    print('Actual game stability PASSED',flush=True)
except Exception as e:
    result['status']='failed';result['error']=str(e)
    raise
finally:
    result['finished_at']=time.strftime('%Y-%m-%d %H:%M:%S')
    (DIST/'game-readiness-report.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf8')
