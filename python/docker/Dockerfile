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
                                python3 \
                                py3-pip && \
    update-ca-certificates && \
    pip3 install aiohttp \
                 bottom \
                 demjson3 \
                 dicttoxml \
                 html5lib \
                 lxml \
                 pycryptodome \
                 romkan && \
    apk del .build-deps && \
    rm -rf /tmp/* && \

    mkdir /data && \
    chown -R nobody:nobody /data

USER nobody

VOLUME /data

CMD python3 -u /data/ircbot/python/main.py
