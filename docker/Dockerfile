#
# Dockerfile for ircbot
#

FROM alpine
MAINTAINER user <user@localhost>

RUN set -ex && \
    apk add --no-cache --virtual .build-deps \
                                build-base \
                                libxml2-dev \
                                libxslt-dev \
                                python3-dev && \
    apk add --no-cache --virtual .run-deps \
                                ca-certificates \
                                libxml2 \
                                libxslt \
                                python3 && \
    update-ca-certificates && \
    pip3 install aiohttp \
                 bottom \
                 demjson \
                 dicttoxml \
                 html5lib \
                 lxml \
                 pycrypto \
                 romkan && \
    apk del .build-deps && \
    rm -rf /tmp/* && \

    mkdir /data && \
    chown -R nobody:nobody /data

USER nobody

VOLUME /data

CMD python3 -u /data/ircbot/main.py \
            >>/data/log 2>&1
