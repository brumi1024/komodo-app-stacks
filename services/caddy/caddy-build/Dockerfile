ARG CADDY_VERSION=2.10.1

FROM caddy:${CADDY_VERSION}-builder-alpine AS builder

RUN xcaddy build \
    --with github.com/mholt/caddy-dynamicdns@v0.0.0-20260711161133-a5890c9df68c \
    --with github.com/caddy-dns/cloudflare@v0.2.4 \
    --with github.com/mholt/caddy-ratelimit@v0.1.0 \
    --with github.com/hslatman/caddy-crowdsec-bouncer/http@v0.13.1

FROM caddy:${CADDY_VERSION} AS caddy

WORKDIR /

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
