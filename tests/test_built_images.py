"""Run locally built DNF images against a disposable MySQL 5.6 database.

Only resources recorded in dist/image-test-state.json are used. Failed runs keep
their isolated resources for diagnosis; cleanup is explicit via --cleanup.
No live server or existing Docker workload is accessed.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
import urllib.request
import uuid
import argparse

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
STATE = DIST / 'image-test-state.json'
GAME = 'dnf-game:local-fix-20261015'
ADMIN = 'dnf-admin:local-fix-20261015'
MYSQL = 'mysql:5.6@sha256:20575ecebe6216036d25dab5903808211f1e9ba63dc7825ac20cb975e34cfcae'

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--game-image', default=GAME)
parser.add_argument('--admin-image', default=ADMIN)
parser.add_argument('--state-file', type=Path, default=STATE)
parser.add_argument('--stable-seconds', type=int, default=300)
parser.add_argument('--mode', choices=['all','split'], default='all')
parser.add_argument('--ubuntu', action='store_true')
parser.add_argument('--cleanup', action='store_true')
options = parser.parse_args()
GAME, ADMIN, STATE = options.game_image, options.admin_image, options.state_file.resolve()
if options.stable_seconds < 1:
    parser.error('--stable-seconds must be positive')
if options.ubuntu:
    from test_ubuntu_images import main
    sys.exit(main(options))
if options.mode != 'all':
    parser.error('Split acceptance is implemented for --ubuntu only')
REPORT_DIR=STATE.parent/(STATE.stem+'-evidence')
REPORT_DIR.mkdir(parents=True,exist_ok=True)

def docker(*args, data=None, check=True):
    r = subprocess.run(['docker', *args], input=data, capture_output=True,
                       text=True, encoding='utf8', errors='replace')
    if check and r.returncode:
        raise RuntimeError(r.stderr + r.stdout)
    return r

def say(s):
    print(time.strftime('%H:%M:%S'), s, flush=True)

def save():
    STATE.write_text(json.dumps(state, indent=2), encoding='utf8')

def sql(query, check=True):
    return docker('exec', '-i', '-e', 'MYSQL_PWD=' + state['password'], state['db'],
                  'mysql', '-uroot', '-N', '--default-character-set=utf8', data=query, check=check)

def wait_for(description, callback, seconds=180):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            result = callback()
            if result:
                say(description + ': OK')
                return result
        except (OSError, RuntimeError, ValueError):
            pass
        time.sleep(3)
    raise RuntimeError('Timeout: ' + description)

def verify_files(image, mapping):
    result = docker('run', '--rm', '--network', 'none', '--entrypoint', 'sha256sum',
                    image, *mapping.keys()).stdout
    for line in result.splitlines():
        digest, target = line.split(None, 1)
        target = target.strip()
        actual = hashlib.sha256((ROOT / mapping[target]).read_bytes()).hexdigest()
        if digest != actual and mapping[target].endswith('.sql'):
            # The pre-Git Windows backend build retained CRLF in SQL. Compare the
            # content after newline normalization only; never waive other changes.
            embedded=docker('run','--rm','--network','none','--entrypoint','cat',image,target).stdout
            assert embedded.replace('\r\n','\n') == (ROOT/mapping[target]).read_text(encoding='utf8').replace('\r\n','\n'), target+': SQL content differs'
            report.setdefault('newline_normalized_files',[]).append(target)
        else:
            assert digest == actual, target + ': image differs from source'
    report['file_hashes'][image] = result.splitlines()
    say(image + ': embedded source hashes match')

def http(path):
    r = docker('exec', state['game'], 'curl', '--fail', '--silent', '--show-error', '--max-time', '5', '-w', '\n%{http_code}', state['url'] + path)
    body, status = r.stdout.rsplit('\n', 1)
    return int(status), body

def cleanup():
    for key in ('admin', 'game', 'db'):
        docker('rm', '-fv', state[key], check=False)
    for name in state['volumes']:
        docker('volume', 'rm', name, check=False)
    docker('network', 'rm', state['network'], check=False)
    state['cleaned_up'] = True
    save()

DIST.mkdir(exist_ok=True)
STATE.parent.mkdir(parents=True, exist_ok=True)
if '--cleanup' in sys.argv:
    state = json.loads(STATE.read_text(encoding='utf8'))
    cleanup()
    say('Removed this test run containers, volumes, and network only')
    sys.exit(0)

assert not STATE.exists() or json.loads(STATE.read_text(encoding='utf8')).get('cleaned_up'), 'Previous test resources need inspection/cleanup first'
prefix = 'dnf-image-test-' + uuid.uuid4().hex[:8]
state = {'network': prefix, 'db': prefix + '-mysql', 'game': prefix + '-game',
         'admin': prefix + '-admin', 'password': secrets.token_hex(16), 'game_password': secrets.token_hex(4),
         'volumes': [prefix + '-game-data', prefix + '-admin-data']}
save()
report = {'started_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'file_hashes': {}, 'checks': []}
try:
    verify_files(GAME, {
        '/home/template/init/prepare_login_seed.sh': 'dnf-game/build/dnf_data/home/template/init/prepare_login_seed.sh',
        '/home/template/init/repair_existing_log_ref.sh': 'dnf-game/build/dnf_data/home/template/init/repair_existing_log_ref.sh',
        '/home/template/init/daily_job/response_time_tables.sh': 'dnf-game/build/dnf_data/home/template/init/daily_job/response_time_tables.sh',
        '/home/template/init/daily_job/daily_job.sh': 'dnf-game/build/dnf_data/home/template/init/daily_job/daily_job.sh',
        '/home/template/init/init.sh': 'dnf-game/build/dnf_data/home/template/init/init.sh',
        '/docker-entrypoint.sh': 'dnf-game/build/dnf_data/docker-entrypoint.sh',
    })
    verify_files(ADMIN, {'/app/entrypoint.sh': 'dnf-server-public/entrypoint.sh',
                         '/app/init.sql.template': 'dnf-server-public/init.sql'})
    for image in (GAME, ADMIN):
        report[image] = json.loads(docker('image', 'inspect', image).stdout)[0]['Id']
    docker('network', 'create', '--internal', state['network'])
    for name in state['volumes']:
        docker('volume', 'create', name)
    docker('run', '-d', '--name', state['db'], '--network', state['network'], '--memory', '1g',
           '-e', 'MYSQL_ROOT_PASSWORD=' + state['password'], '-e', 'MYSQL_ROOT_HOST=%', MYSQL,
           '--sql-mode=NO_ENGINE_SUBSTITUTION', '--max-allowed-packet=64M')
    wait_for('MySQL 5.6 ready', lambda: docker('exec', '-e', 'MYSQL_PWD='+state['password'],
             state['db'], 'mysql', '-h127.0.0.1', '-uroot', '-N', '-e', 'SELECT 1;', check=False).returncode == 0)
    report['mysql_version'] = sql('SELECT VERSION();').stdout.strip()
    db_info = json.loads(docker('inspect', state['db']).stdout)[0]
    dbip = db_info['NetworkSettings']['Networks'][state['network']]['IPAddress']
    state['db_ip'] = dbip
    # Matching ephemeral client-authentication key pair; never use production keys.
    docker('run', '--rm', '--network', 'none', '--entrypoint', 'sh',
           '-v', state['volumes'][1]+':/app/data', '-v', state['volumes'][0]+':/game-data', ADMIN,
           '-c', 'openssl genpkey -algorithm RSA -out /app/data/private.key -pkeyopt rsa_keygen_bits:2048 && '
                 'chmod 600 /app/data/private.key && openssl rsa -pubout -in /app/data/private.key '
                 '-out /app/data/publickey.pem && cp /app/data/publickey.pem /game-data/publickey.pem')
    env = {'SERVER_TYPE':'ALL', 'SERVER_GROUP':'3', 'SERVER_GROUP_DB':'cain', 'OPEN_CHANNEL':'11,52',
           'CLIENT_POOL_SIZE':'3', 'PUBLIC_IP':'127.0.0.1', 'CORE_PUBLIC_IP':'127.0.0.1',
           'P2P_PUBLIC_IP':'127.0.0.1', 'P2P_RELAY_INDEX':'1', 'MAIN_BRIDGE_IP':'127.0.0.1',
           'MAIN_MYSQL_HOST':dbip, 'MAIN_MYSQL_PORT':'3306', 'MAIN_MYSQL_ROOT_PASSWORD':state['password'],
           'MAIN_MYSQL_GAME_ALLOW_IP':'%', 'MYSQL_HOST':dbip, 'MYSQL_PORT':'3306',
           'MYSQL_GAME_ALLOW_IP':'%', 'DNF_DB_ROOT_PASSWORD':state['password'],
           'DNF_DB_GAME_PASSWORD':state['game_password'], 'WEB_PASS':secrets.token_hex(12),
           'GM_PASSWORD':secrets.token_hex(12)}
    args=[]
    for k,v in env.items(): args.extend(['-e',k+'='+v])
    docker('run','-d','--name',state['game'],'--network',state['network'],'--memory','10g',
           '--shm-size','8g','--cpus','4','-v',state['volumes'][0]+':/data',*args,GAME)
    save()
    wait_for('Game schema imported', lambda: sql('SELECT 1 FROM taiwan_cain_2nd.member_avatar_coin LIMIT 1; '
             'SELECT 1 FROM taiwan_login.log_query_ref LIMIT 1;', False).returncode == 0, 300)
    row = sql("SELECT q_id FROM taiwan_login.log_query_ref WHERE query_hash='6d986dad283ff5a4';").stdout.strip()
    assert row == '50939', row
    assert sql('SELECT MAX(q_id) < 65535 FROM taiwan_login.log_query_ref;').stdout.strip() == '1'
    report['checks'].append('Fresh game import remapped known seed q_id to 50939; no exhausted counter')
    sql("INSERT INTO taiwan_login.log_query_ref(query_hash,query) VALUES ('buildimagecheck','SELECT 1');")
    report['checks'].append('New log_query_ref INSERT succeeded on fresh imported database')
    wait_for('Monthly response log tables created', lambda: sql("SELECT COUNT(*) FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA='taiwan_cain_log' AND TABLE_NAME IN (CONCAT('log_response_time_',DATE_FORMAT(NOW(),'%Y%m')),"
        "CONCAT('log_response_time_',DATE_FORMAT(DATE_ADD(NOW(),INTERVAL 1 MONTH),'%Y%m')));").stdout.strip()=='2', 180)
    report['checks'].append('Current and next month response log tables exist')
    adminenv={'SPRING_DATASOURCE_URL':'jdbc:mysql://'+dbip+':3306/dnf_service?useUnicode=true&characterEncoding=utf8&useSSL=false&autoReconnect=true',
              'SPRING_DATASOURCE_USERNAME':'root','SPRING_DATASOURCE_PASSWORD':state['password'],
              'MYSQL_INIT_SSL_MODE':'disabled', 'JAVA_TOOL_OPTIONS':'-Xmx512m'}
    args=[]
    for k,v in adminenv.items(): args.extend(['-e',k+'='+v])
    docker('run','-d','--name',state['admin'],'--network',state['network'],'--memory','1g',
           '-v',state['volumes'][1]+':/app/data',*args,ADMIN)
    info=json.loads(docker('inspect',state['admin']).stdout)[0]
    adminip=info['NetworkSettings']['Networks'][state['network']]['IPAddress']
    state['url']='http://'+adminip
    save()
    wait_for('Backend version API HTTP 200',lambda: http('/api/v1/client/version/1.0.0')[0]==200,180)
    assert http('/')[0]==200
    assert docker('exec',state['admin'],'test','-f','/app/data/.db_initialized').returncode==0
    assert sql("SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='d_taiwan' "
               "AND TABLE_NAME='accounts' AND COLUMN_NAME IN ('admin','parent_uid','isRobot');").stdout.strip()=='3'
    report['backend_table_count']=sql("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='dnf_service';").stdout.strip()
    report['checks'].append('Backend fresh initialization with MYSQL_INIT_SSL_MODE=disabled; marker, account columns, HTTP frontend/API pass')
    bootstrap=(ROOT/'deploy/shared/bootstrap-admin.sql.example').read_text(encoding='utf8')
    bootstrap=bootstrap.replace('CHANGE_ME_NEW_PRIVATE_ADMIN_PASSWORD',secrets.token_hex(12))
    bootstrap=bootstrap.replace('CHANGE_ME_DIFFERENT_PRIVATE_TEMP_SECRET',secrets.token_hex(12))
    sql(bootstrap)
    assert sql("SELECT admin FROM d_taiwan.accounts WHERE accountname='admin';").stdout.strip()=='1'
    assert sql('SELECT COUNT(*) FROM dnf_service.ADMIN_TEMP_PASSWORD WHERE id=1;').stdout.strip()=='1'
    report['checks'].append('Separate bootstrap-admin.sql.example creates test administrator and authorization row')
    docker('restart',state['admin'])
    wait_for('Backend restart HTTP 200',lambda: http('/api/v1/client/version/1.0.0')[0]==200,90)
    assert 'DB already initialized.' in docker('logs',state['admin']).stdout
    assert sql("SELECT COUNT(*) FROM d_taiwan.accounts WHERE accountname='admin';").stdout.strip()=='1'
    report['checks'].append('Backend restart skips destructive SQL and preserves administrator')
    # Require identical channel supervisor PIDs over multiple original crash cycles.
    def channels():
        r=docker('exec',state['game'],'supervisorctl','status',check=False).stdout
        matches=re.findall(r'^game:(game_siroco(?:11|52))\s+RUNNING\s+pid (\d+),',r,re.M)
        return dict(matches) if len(matches)==2 else None
    def actual_game_ready():
        processes=docker('exec',state['game'],'pgrep','-x','df_game_r',check=False).stdout.split()
        sockets=docker('exec',state['game'],'cat','/proc/net/tcp').stdout
        ports={int(line.split()[1].split(':')[1],16) for line in sockets.splitlines()[1:] if line.split()[3]=='0A'}
        return processes if len(processes)==2 and {30011,30052}.issubset(ports) else None
    actual_pids=wait_for('Actual game processes and both TCP ports ready',actual_game_ready,600)
    pids=wait_for('Both game channel wrappers RUNNING',channels,240)
    say('Observing channel PIDs for '+str(options.stable_seconds)+' seconds: '+str(pids))
    elapsed=0
    while elapsed < options.stable_seconds:
        interval=min(10,options.stable_seconds-elapsed)
        time.sleep(interval)
        elapsed+=interval
        assert channels()==pids, 'Channel restarted during stability observation'
        assert actual_game_ready()==actual_pids, 'Actual game PID or listening port changed'
        if elapsed%60==0: say('Stable channel observation: '+str(elapsed)+' seconds')
    report['checks'].append('Both channel supervisor PIDs stable for '+str(options.stable_seconds)+' seconds')
    report['supervisor_status']=docker('exec',state['game'],'supervisorctl','status',check=False).stdout
    report['game_processes']=docker('exec',state['game'],'sh','-c',"ps -eo pid,etime,args | grep '[d]f_game_r'").stdout
    assert len([l for l in report['game_processes'].splitlines() if './df_game_r ' in l])>=2
    report['status']='passed'
    say('Full built-image test PASSED')
except Exception as exc:
    report['status']='failed'
    report['error']=str(exc)
    say('FAILED: '+str(exc))
    raise
finally:
    report['finished_at']=time.strftime('%Y-%m-%d %H:%M:%S')
    for key in ('game','admin','db'):
        result=docker('logs',state[key],check=False)
        text=result.stdout+result.stderr
        for value in (state.get('password',''),state.get('game_password','')):
            if value: text=text.replace(value,'[REDACTED]')
        (REPORT_DIR/('test-'+key+'.log')).write_text(text,encoding='utf8')
    (REPORT_DIR/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
