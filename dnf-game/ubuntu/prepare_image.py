"""Derive Ubuntu scripts from shared sources at build time; fail on upstream drift.

No source checkout is edited. SQL repair logic remains shared with CentOS.
"""
from pathlib import Path
import re
import shutil

BASE=Path('/opt/dnf/ubuntu')
INIT=Path('/home/template/init')

def replace(text, old, new, count=1):
    if text.count(old)!=count:
        raise ValueError('Shared source changed; review Ubuntu adaptation: '+old[:90])
    return text.replace(old,new)

def write(path,text):
    path.write_text(text); path.chmod(0o755)

def require_user_pvf(text):
    start = text.index('  if [ ! -f "/data/Script.pvf" ];then')
    end = text.index('\n  fi', start) + len('\n  fi')
    return text[:start] + '  python3 /opt/dnf/ubuntu/pvf.py || exit 1' + text[end:]

def remove_legacy_gateway(entry, init, starter):
    def cut(text, first, after):
        start=text.index(first)
        end=text.index(after,start)
        return text[:start]+text[end:]
    entry=cut(entry,'# 清理root下文件','# 复制待使用文件')
    entry=cut(entry,'# 重置root目录','# 重设supervisor web网页密码')
    init=cut(init,'  # 判断Config.ini文件是否初始化过','  # 判断每日脚本是否初始化')
    init=cut(init,'  # 入口在其他大区CORE服务','  # 拷贝core服务supervisor配置文件')
    starter=replace(starter,'    echo "starting tongyi_gate ..."\n    supervisorctl restart tongyi_gate\n','')
    starter=starter.replace('bridge、Gate以及channel','bridge以及channel')
    return entry,init,starter

def main():
    for path in BASE.rglob('*'):
        if path.is_file() and path.suffix in ('.sh','.py'):
            write(path,path.read_text())
    write(BASE/'mysql',(BASE/'mysql').read_text())
    shutil.copyfile(BASE/'mysql','/usr/local/bin/mysql')
    Path('/usr/local/bin/mysql').chmod(0o755)
    # These two daemons actually bind this_ip; advertised public/NAT addresses
    # do not belong to a bridge-network container. Game routes use CORE_PUBLIC_IP.
    for service in ('auction','point'):
        path=Path('/home/template/neople')/service/'cfg/server.cfg'
        write(path,replace(path.read_text(),'this_ip = PUBLIC_IP','this_ip = 0.0.0.0'))
    legacy=(BASE/'legacy-entrypoint.sh').read_text()
    legacy,init,starter=remove_legacy_gateway(legacy,(INIT/'init.sh').read_text(),(INIT/'starter/start_program.sh').read_text())
    for filename in ('Config.ini','privatekey.pem'):
        (INIT/filename).unlink(missing_ok=True)
    for filename in ('gate.conf.template','gate.conf'):
        (Path('/etc/supervisor/conf.d')/filename).unlink(missing_ok=True)
    entry='#!/bin/bash\n'+legacy[legacy.index('# 清除MONITOR_PUBLIC_IP文件'):]
    entry=replace(entry,'mkdir -p /data/log/netbird\n','')
    entry=replace(entry,'mkdir -p /data/log/tailscale\n','')
    entry=replace(entry,'mkdir -p /data/netbird\n','')
    entry=replace(entry,'mkdir -p /data/tailscale\n','')
    entry=replace(entry,'supervisord -c /etc/supervisord.conf','exec /usr/bin/supervisord -c /etc/supervisord.conf')
    # Clear current-run evidence before initialization; health cannot reuse old logs.
    entry=entry.replace('# 初始化数据','date +%s > /run/dnf/started-at\n# 初始化数据',1)
    write(BASE/'generated-entrypoint.sh',entry)
    (BASE/'legacy-entrypoint.sh').unlink()
    start=init.index('  # 初始化本地数据库')
    end=init.index('  # 初始化主数据库',start)
    init=init[:start]+init[end:]
    write(INIT/'init.sh',require_user_pvf(init))
    (INIT/'Script.tgz').unlink(missing_ok=True)
    (INIT/'Script.pvf').unlink(missing_ok=True)
    (INIT/'init_local_db.sh').unlink()
    for filename in ('init_main_db.sh','init_server_group_db.sh'):
        path=INIT/filename
        text=path.read_text().replace('select db_name, db_ip, db_port, db_passwd','select db_name, db_ip, db_port')
        # Keep shared SQL, but make failed import/grant/update fatal (not probe errors).
        text=re.sub(r'(?m)^(\s*)mysql (.*<<EOF)$',r'\1mysql \2',text)
        text=text.replace('\nEOF\n','\nEOF\n[ "$?" -eq 0 ] || exit 1\n')
        write(path,text)
    for path in (INIT/'run').glob('*.sh'):
        text=path.read_text()
        text='#!/bin/bash\nsource /opt/dnf/ubuntu/wait.sh\n'+text
        pattern=r'counter=0\nwhile \[ \$counter -lt \d+ \]\ndo\n  if nc -zv (.*?) (.*?) 2>&1 \| grep succeeded >/dev/null ; then.*?\ndone'
        text=re.sub(pattern,lambda m: 'wait_tcp "'+m[1]+'" '+m[2]+' core-service || exit 1',text,flags=re.S)
        pattern=r'while \[ -z "\$\(cat /data/monitor_ip/MONITOR_PUBLIC_IP 2>/dev/null \|\| true\)" \];\ndo.*?\ndone'
        text=re.sub(pattern,'wait_file /data/monitor_ip/MONITOR_PUBLIC_IP || exit 1',text,flags=re.S)
        text=text.replace('echo "compiling stun_hook.so..."','')
        text=text.replace('gcc -shared -fPIC -o stun_hook.so stun_hook.c -ldl -Wall -O2','')
        text=re.sub(r'(?m)^LD_PRELOAD=(\S+) (\./\S+)',r'DNF_GAME_PRELOAD=\1 /opt/dnf/ubuntu/run-game \2',text)
        text=re.sub(r'(?m)^(\./(?:df_\w+|gunnersvr|zergsvr|secagent)\b)',r'/opt/dnf/ubuntu/run-game \1',text)
        if path.name=='start_game.sh':
            # Flush only the patched executable. Global sync can block on
            # unrelated host/FUSE mounts (observed during clean-clone builds).
            text=replace(text,'    sync\n','    timeout 30 sync df_game_r || exit 1\n')
            text=replace(text,'DNF_GAME_PRELOAD=/dp2/libhook.so',
                         'python3 /opt/dnf/ubuntu/channel_logs.py "$channel_name" || exit 1\nDNF_GAME_PRELOAD=/dp2/libhook.so')
        if 'grep succeeded' in text or 'while [ -z' in text:
            raise ValueError('Unadapted wait in '+str(path))
        write(path,text)
    for name in ('start_mysql_proxy.sh','start_main_mysql_proxy.sh'):
        path=INIT/'mysql_proxy'/name
        write(path,path.read_text().replace('TCP-LISTEN:3306,','TCP-LISTEN:3306,bind=127.0.0.1,').replace('TCP-LISTEN:3307,','TCP-LISTEN:3307,bind=127.0.0.1,'))
    starter='#!/bin/bash\nset -e\nsource /opt/dnf/ubuntu/wait.sh\n'+starter[starter.index('# 启动monitor_ip'):]
    a=starter.index('while true; do'); b=starter.index('\ndone',a)+len('\ndone')
    starter=starter[:a]+'wait_file /data/monitor_ip/MONITOR_PUBLIC_IP || exit 1'+starter[b:]
    # Propagate failed supervisor actions while allowing successful oneshot services.
    starter=starter.replace('supervisorctl restart','supervisorctl -c /etc/supervisord.conf restart')
    write(INIT/'starter/start_program.sh',starter)
    write(INIT/'monitor_ip/monitor_ip.sh','#!/bin/bash\nexec python3 /opt/dnf/ubuntu/monitor_ip.py\n')
    for name in ('auto_public_ip.sh','get_ddns_ip.sh'):
        path=INIT/'monitor_ip'/name
        write(path,path.read_text().replace('curl -s','curl --connect-timeout 2 --max-time 2 -fsS'))
    for name in ('netbird.conf','tailscale.conf'):
        (Path('/etc/supervisor/conf.d')/name).unlink(missing_ok=True)
    # Legacy daemon wrappers return 0 after their child exits. Every long-lived
    # role service must restart even after that status (e.g. DB outage auction).
    for name in ('core.conf.template','p2p.conf.template','tss.conf.template'):
        path=Path('/etc/supervisor/conf.d')/name
        write(path,path.read_text().replace('autorestart=unexpected','autorestart=true'))
    monitor=Path('/etc/supervisor/conf.d/monitor_ip.conf')
    write(monitor,replace(monitor.read_text(),'autostart=true','autostart=false\nstartsecs=0'))
    supervisor=Path('/etc/supervisord.conf')
    text=supervisor.read_text().replace('environment=ENVIRONMENT','')
    text=text.replace('port=0.0.0.0:180','port=127.0.0.1:180')
    write(supervisor,text)
    # The shared entry uses supervisorctl without arguments; Ubuntu searches this path.
    Path('/etc/supervisor/supervisord.conf').unlink(missing_ok=True)
    Path('/etc/supervisor/supervisord.conf').symlink_to('/etc/supervisord.conf')
    for section in ('run','monitor_ip'):
        destination=BASE/'managed'/section
        destination.mkdir(parents=True,exist_ok=True)
        for path in (INIT/section).glob('*.sh'):
            if section=='monitor_ip' and path.name=='monitor_ip.sh': continue
            shutil.copyfile(path,destination/path.name)
    # user_daily_script.sh remains user-owned and is not upgraded as a managed script.
    for name in ('client','server'):
        write(INIT/'relay'/(name+'.sh'),'#!/bin/bash\nexec python3 /opt/dnf/ubuntu/relay.py '+name+'\n')

if __name__=='__main__': main()
