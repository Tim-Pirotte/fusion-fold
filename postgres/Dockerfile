FROM dhi.io/postgres:18.4-dev AS build-stage

COPY entrypoint.sh /tmp/entrypoint.sh
RUN chmod +x /tmp/entrypoint.sh

FROM dhi.io/postgres:18.4 AS runtime-stage

COPY --from=build-stage /tmp/entrypoint.sh /usr/local/bin/entrypoint.sh
# COPY init.sql /docker-entrypoint-initdb.d/init.sql

ENTRYPOINT [ "entrypoint.sh" ]
