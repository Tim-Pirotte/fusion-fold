#!/usr/bin/env bash
set -Eeu -o pipefail

file_env() {
    local var="$1"
    local fileVar="${var}_FILE"
    local default="${2:-}"

    local value="$default"

    if [ -n "${!fileVar:-}" ]; then
        value="$(< "${!fileVar}")"
    elif [ -n "${!var:-}" ]; then
        value="${!var}"
    fi

    export "$var"="$value"
    unset "$fileVar"
}

file_env 'POSTGRES_USER' 'postgres'
file_env 'POSTGRES_DB' "$POSTGRES_USER"

INIT_MARKER="$PGDATA/PG_VERSION"
IS_NEW_DB=false
[ ! -s "$INIT_MARKER" ] && IS_NEW_DB=true

docker-entrypoint.sh "$@" &
PG_PID=$!

if [ "$IS_NEW_DB" = "true" ]; then
    until psql -v ON_ERROR_STOP=1 \
        --username "$POSTGRES_USER" \
        --dbname "$POSTGRES_DB" \
        -c '\q' 2>/dev/null; do
        sleep 0.5
    done

    echo "INIT: Running init scripts..."

    psql -v ON_ERROR_STOP=1 \
        --username "$POSTGRES_USER" \
        --dbname "$POSTGRES_DB" \
        -f "/docker-entrypoint-initdb.d/init.sql"

    echo "INIT: Done."
fi

wait $PG_PID
