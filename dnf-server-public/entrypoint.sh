#!/bin/sh
set -eu

mkdir -p /app/data
if [ ! -f /app/data/private.key ] || [ ! -f /app/data/publickey.pem ]; then
    if [ -f /app/data/private.key ] || [ -f /app/data/publickey.pem ]; then
        echo "Incomplete RSA key pair; restore the matching pair before starting." >&2
        exit 1
    fi
    echo "Generating RSA key pair (2048bit PKCS#8)..."
    openssl genpkey -algorithm RSA -out /app/data/private.key -pkeyopt rsa_keygen_bits:2048
    chmod 600 /app/data/private.key
    openssl rsa -pubout -in /app/data/private.key -out /app/data/publickey.pem
else
    echo "Keys found in /app/data."
fi

MARKER_FILE=/app/data/.db_initialized
if [ ! -f "$MARKER_FILE" ]; then
    : "${SPRING_DATASOURCE_URL:?Set SPRING_DATASOURCE_URL}"
    : "${SPRING_DATASOURCE_USERNAME:?Set SPRING_DATASOURCE_USERNAME}"
    case "$SPRING_DATASOURCE_URL" in
        jdbc:mysql://*) ;;
        *) echo "Expected jdbc:mysql://host:port/database URL" >&2; exit 1 ;;
    esac
    PROTO_REMOVED=${SPRING_DATASOURCE_URL#jdbc:mysql://}
    DB_HOST=$(printf '%s\n' "$PROTO_REMOVED" | sed -e 's|:.*||' -e 's|/.*||' -e 's|?.*||')
    DB_PORT=$(printf '%s\n' "$PROTO_REMOVED" | sed -n 's|.*:\([0-9]*\).*|\1|p')
    DB_PORT=${DB_PORT:-3306}
    DB_NAME=$(printf '%s\n' "$PROTO_REMOVED" | cut -d/ -f2- | cut -d? -f1)
    case "$DB_NAME" in ''|*[!a-zA-Z0-9_]*) echo "Invalid database name" >&2; exit 1 ;; esac
    export DB_NAME

    # The CLI has its own TLS settings; JDBC useSSL=false does not affect it.
    # Runtime image installs MariaDB client. Only opt out explicitly for legacy DBs.
    set --
    case "${MYSQL_INIT_SSL_MODE:-auto}" in
        auto) ;;
        disabled) set -- --skip-ssl ;;
        *) echo "MYSQL_INIT_SSL_MODE must be auto or disabled" >&2; exit 1 ;;
    esac
    db_query() {
        mysql "$@" -h "$DB_HOST" -P "$DB_PORT" -u "$SPRING_DATASOURCE_USERNAME" \
            -p"${SPRING_DATASOURCE_PASSWORD:-}"
    }
    echo "Checking first initialization at $DB_HOST:$DB_PORT, database $DB_NAME..."
    # init.sql contains DROP TABLE and ADD COLUMN. Never replay it on a partial DB.
    existing=$(db_query "$@" -N -e "SELECT
        (SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='$DB_NAME') +
        (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='d_taiwan'
         AND TABLE_NAME='accounts' AND COLUMN_NAME IN ('admin','parent_uid','isRobot'));")
    if [ "$existing" != 0 ]; then
        echo "Existing/partial backend schema without initialization marker; inspect and complete it manually. No SQL imported." >&2
        exit 1
    fi
    envsubst '${DB_NAME}' < /app/init.sql.template > /app/init.sql
    if ! db_query "$@" < /app/init.sql; then
        echo "Database initialization failed; stopping before Nginx/Java. No success marker written." >&2
        exit 1
    fi
    touch "$MARKER_FILE"
    echo "Database initialized successfully."
else
    echo "DB already initialized."
fi

envsubst '${NGINX_PORT} ${SERVER_PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
service nginx start
exec java -jar /app/app.jar
