FROM debian:bookworm-slim

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
        iperf3 \
        iproute2 \
        iputils-ping \
        curl \
        nginx \
        wrk \
    && dd if=/dev/zero of=/var/www/html/archivo-10m.bin bs=1M count=10 \
    && dd if=/dev/zero of=/var/www/html/archivo-256k.bin bs=1K count=256 \
    && chmod 0644 /var/www/html/archivo-10m.bin \
    && chmod 0644 /var/www/html/archivo-256k.bin \
    && rm -rf /var/lib/apt/lists/*

CMD ["/bin/sh"]
