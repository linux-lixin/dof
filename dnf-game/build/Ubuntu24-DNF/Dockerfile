# syntax=docker/dockerfile:1
# This manifest is pinned; build on an x86_64 Docker host using its default platform.
FROM ubuntu:24.04@sha256:534baea6a22c03a63003dbc8dbe78fe34bc0d7e595d9a9dc9834884ff530eb55 AS runtime
ENV TZ=Asia/Shanghai
RUN dpkg --add-architecture i386 \
 && apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates tzdata python3 supervisor socat netcat-openbsd mariadb-client \
    bash coreutils findutils grep sed gawk perl procps psmisc binutils openssl curl iproute2 net-tools \
    libc6:i386 libstdc++6:i386 libgcc-s1:i386 zlib1g:i386 \
    libstdc++6 libgcc-s1 zlib1g libcrypt1 \
 && rm -rf /var/lib/apt/lists/* \
 && ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

FROM runtime AS hooks
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends gcc gcc-multilib libc6-dev autoconf automake libtool make \
 && rm -rf /var/lib/apt/lists/*
COPY build/dnf_data/home/template/neople/stun/stun_hook.c /tmp/stun_hook.c
RUN gcc -shared -fPIC -o /tmp/stun_hook.so /tmp/stun_hook.c -ldl -Wall -O2
COPY build/Ubuntu24-DNF/geoip_1.6.12.orig.tar.gz /tmp/geoip.tar.gz
RUN echo '99b119f8e21e94f1dfd6d49fbeed29a70df1544896e76cd456f25e397b07d476  /tmp/geoip.tar.gz' | sha256sum -c - \
 && mkdir /tmp/geoip && tar -xzf /tmp/geoip.tar.gz -C /tmp/geoip --strip-components=1 \
 && cd /tmp/geoip && autoreconf -fi \
 && CC='gcc -m32' ./configure --host=i686-linux-gnu --prefix=/opt/dnf/compat/i386 --disable-static \
 && make -j2 && make install
COPY build/Ubuntu24-DNF/openssl-0.9.8zh.tar.gz /tmp/openssl.tar.gz
COPY build/Ubuntu24-DNF/build-openssl.sh /tmp/build-openssl.sh
RUN echo 'f1d9f3ed1b85a82ecf80d0e2d389e1fda3fca9a4dba0bf07adbf231e1a5e2fd6  /tmp/openssl.tar.gz' | sha256sum -c - \
 && mkdir /tmp/openssl && tar -xzf /tmp/openssl.tar.gz -C /tmp/openssl --strip-components=1 \
 && sed -i 's/\r$//' /tmp/build-openssl.sh && sh /tmp/build-openssl.sh
COPY build/Ubuntu24-DNF/audit/geoip-probe.c /tmp/geoip-probe.c
RUN gcc -m32 -I/tmp/geoip/libGeoIP -L/opt/dnf/compat/i386/lib -o /tmp/geoip-probe /tmp/geoip-probe.c -lGeoIP
COPY build/Ubuntu24-DNF/legacy-shm.c /tmp/legacy-shm.c
COPY build/Ubuntu24-DNF/audit/shm-probe.c /tmp/shm-probe.c
RUN echo 'd8fb57b31d9b29ad576e0100d6fa67e71aa19c3e6d994e5e0a5957e41caec772  /tmp/legacy-shm.c' | sha256sum -c - \
 && gcc -m32 -shared -fPIC -Wall -Wextra -Werror -O2 -o /tmp/liblegacy-shm.so /tmp/legacy-shm.c -ldl \
 && gcc -m32 -Wall -Wextra -Werror -o /tmp/shm-probe /tmp/shm-probe.c -lrt

FROM runtime AS game
COPY build/dnf_data/home/template/ /home/template/
COPY build/dnf_data/TeaEncrypt /TeaEncrypt
COPY build/dnf_data/etc/supervisor/ /etc/supervisor/
COPY build/dnf_data/etc/supervisord.conf /etc/supervisord.conf
COPY --from=hooks /tmp/stun_hook.so /home/template/neople/stun/stun_hook.so
COPY --from=hooks /opt/dnf/compat/i386/lib/libGeoIP.so.1.6.12 /opt/dnf/compat/i386/libGeoIP.so.1
COPY --from=hooks /tmp/geoip/COPYING /opt/dnf/licenses/GeoIP-COPYING
COPY --from=hooks /tmp/geoip/LICENSE /opt/dnf/licenses/GeoIP-LICENSE
COPY --from=hooks /tmp/geoip-probe /opt/dnf/audit/geoip-probe
COPY --from=hooks /tmp/liblegacy-shm.so /opt/dnf/compat/i386/liblegacy-shm.so
COPY --from=hooks /tmp/shm-probe /opt/dnf/audit/shm-probe
COPY build/Ubuntu24-DNF/SHM-COMPAT-LICENSE /opt/dnf/licenses/SHM-COMPAT-LICENSE
COPY build/Ubuntu24-DNF/GeoIP.dat /opt/dnf/compat/i386/share/GeoIP/GeoIP.dat
COPY build/Ubuntu24-DNF/GEOIP-DATA-README /opt/dnf/licenses/GeoIP-DATA-README
COPY --from=hooks /tmp/openssl/libssl.so.6 /tmp/openssl/libcrypto.so.6 /opt/dnf/compat/amd64/
COPY --from=hooks /tmp/openssl/LICENSE /opt/dnf/licenses/OpenSSL-0.9.8-LICENSE
COPY build/Ubuntu24-DNF/libmysqlclient.so.15.0.0 /opt/dnf/compat/amd64/libmysqlclient.so.15
COPY build/Ubuntu24-DNF/MYSQL-COPYING /opt/dnf/licenses/MySQL-COPYING
COPY build/Ubuntu24-DNF/compat-lock.json /opt/dnf/audit/compat-lock.json
COPY build/Ubuntu24-DNF/run-game /opt/dnf/ubuntu/run-game
COPY build/Ubuntu24-DNF/audit/elf-audit.py /opt/dnf/audit/elf-audit.py
RUN mkdir -p /opt/dnf/compat/i386 /opt/dnf/compat/amd64 \
 && rm -rf /home/template/init/netbird /home/template/init/tailscale \
 && rm -rf /home/template/root \
 && cp /home/template/neople/game/libnxencryption.so /opt/dnf/compat/i386/ \
 && echo 'cd1d9db9700d581e40547ff609a26bcf04415198fe9f3e4ecfc910eefc437f76  /opt/dnf/compat/i386/libnxencryption.so' | sha256sum -c - \
 && echo 'c9fc03966602b5072775cfba906a141565e48c9baf1c531db6669fcc5695de0f  /opt/dnf/compat/amd64/libmysqlclient.so.15' | sha256sum -c - \
 && echo '58fcdeaac15e222a744b27333a776a2b91dc493d212acbe971ba6b987265a73c  /opt/dnf/compat/i386/share/GeoIP/GeoIP.dat' | sha256sum -c - \
 && find /home/template -type f -name '*.sh' -exec sed -i 's/\r$//' {} + \
 && sed -i 's/\r$//' /opt/dnf/ubuntu/run-game \
 && chmod 755 /TeaEncrypt /opt/dnf/ubuntu/run-game \
 && find /home/template -type f -exec chmod u+x {} + \
 && python3 /opt/dnf/audit/elf-audit.py /home/template --extra /TeaEncrypt --output /opt/dnf/audit/elf-report.json \
 && python3 /opt/dnf/audit/elf-audit.py /opt/dnf/compat --output /opt/dnf/audit/compat-report.json \
 && LD_LIBRARY_PATH=/opt/dnf/compat/i386 /opt/dnf/audit/geoip-probe > /opt/dnf/audit/geoip-start-proof.txt \
 && /opt/dnf/ubuntu/run-game /opt/dnf/audit/shm-probe > /opt/dnf/audit/shm-start-proof.txt \
 && DNF_GAME_PRELOAD=/home/template/init/libhook.so /opt/dnf/ubuntu/run-game /opt/dnf/audit/shm-probe >> /opt/dnf/audit/shm-start-proof.txt \
 && dpkg-query -W > /opt/dnf/audit/packages.tsv

FROM game AS final
COPY ubuntu/ /opt/dnf/ubuntu/
COPY build/dnf_data/docker-entrypoint.sh /opt/dnf/ubuntu/legacy-entrypoint.sh
RUN python3 /opt/dnf/ubuntu/prepare_image.py \
 && python3 /opt/dnf/ubuntu/tss_config.py
WORKDIR /root
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 CMD ["python3", "/opt/dnf/ubuntu/health.py"]
ENTRYPOINT ["/bin/bash", "/opt/dnf/ubuntu/entrypoint.sh"]
