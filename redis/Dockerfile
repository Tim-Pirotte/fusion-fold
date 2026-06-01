FROM dhi.io/redis:8

COPY redis.conf /etc/redis/redis.conf
COPY users.acl /etc/redis/users.acl

CMD ["redis-server", "/etc/redis/redis.conf"]
