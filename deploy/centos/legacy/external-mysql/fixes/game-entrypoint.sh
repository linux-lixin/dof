#!/bin/bash
# Compatibility overlay for the pinned 2.1.9.fix1 image, whose init.sh is older.
set -euo pipefail
if [ ! -d /home/template/init/init_sql ]; then
    mkdir -p /home/template/init/init_sql
    tar -xzf /home/template/init/init_sql.tgz -C /home/template/init/init_sql
fi
bash /opt/dnf-fixes/prepare_login_seed.sh /home/template/init/init_sql
exec /bin/bash /docker-entrypoint.sh "$@"
