# CMaNGOS-TBC (2.4.3) server image: mangosd, realmd, extractors, and the DB installer.
# Sources are cloned inside the build so shell scripts keep LF line endings.

FROM ubuntu:24.04 AS build

ARG CMANGOS_COMMIT
ARG TBCDB_COMMIT
ARG BUILD_JOBS=8

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential cmake git ca-certificates \
        libboost-program-options-dev libboost-thread-dev libboost-regex-dev \
        libboost-serialization-dev libboost-filesystem-dev \
        libssl-dev libmariadb-dev libmariadb-dev-compat libicu-dev zlib1g-dev libbz2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git init -q mangos-tbc && cd mangos-tbc \
    && git fetch -q --depth 1 https://github.com/cmangos/mangos-tbc.git ${CMANGOS_COMMIT} \
    && git checkout -q FETCH_HEAD
RUN git init -q tbc-db && cd tbc-db \
    && git fetch -q --depth 1 https://github.com/cmangos/tbc-db.git ${TBCDB_COMMIT} \
    && git checkout -q FETCH_HEAD

RUN cmake -S mangos-tbc -B build \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/opt/cmangos \
        -DBUILD_EXTRACTORS=ON \
        -DPCH=ON \
    && cmake --build build --parallel ${BUILD_JOBS} \
    && cmake --install build \
    && cp mangos-tbc/contrib/extractor_scripts/config.json /opt/cmangos/bin/tools/


FROM ubuntu:24.04

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libboost-program-options1.83.0 libboost-thread1.83.0 libboost-regex1.83.0 \
        libboost-serialization1.83.0 libboost-filesystem1.83.0 \
        libssl3t64 libmariadb3 libicu74 zlib1g libbz2-1.0 \
        mariadb-client ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /opt/cmangos /opt/cmangos
# InstallFullDB.sh only needs the core's sql/ tree
COPY --from=build /src/mangos-tbc/sql /opt/mangos-tbc/sql
COPY --from=build /src/tbc-db /opt/tbc-db
COPY scripts/ /scripts/

# Fail the build early if any shared library is missing at runtime
RUN sed -i 's/\r$//' /scripts/*.sh && chmod +x /scripts/*.sh \
    && cd /opt/cmangos/bin \
    && ! ldd mangosd realmd tools/ad tools/vmap_extractor tools/vmap_assembler tools/MoveMapGen | grep "not found"

WORKDIR /opt/cmangos/bin
ENTRYPOINT ["/scripts/entrypoint.sh"]
