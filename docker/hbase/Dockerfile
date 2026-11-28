# HBase 2.6.4 in one container, for the local stack and the pipeline (card SBJ17-14).
# Built from Apache's own binary, checked against Apache's published SHA-512. Java 8 (Amazon Corretto 8),
# as on the job's side for now; the move to Java 17 is a later card.
# Build: docker compose -f docker/local/docker-compose.yml build hbase   (or: docker build -t salesbatch-hbase:2.6.4 docker/hbase)
FROM amazoncorretto:8@sha256:4e56b677c48df6cd0bedf4441cd9706159fca367d9b970c7251e9e1228ee1b03

ARG HBASE_VERSION=2.6.4
ARG HBASE_SHA512=eb3af96419b8e10fb5a74c291e7e689b9dfc8b988f92018ba8a7f10939118d8497aa9d966af92806600491394da5c1e3206903f1ebb8f0547ed7d712333570c0

RUN yum install -y -q tar gzip hostname procps-ng which findutils gawk grep \
 && yum clean all && rm -rf /var/cache/yum
RUN curl -fsSL -o /tmp/hbase.tgz "https://archive.apache.org/dist/hbase/${HBASE_VERSION}/hbase-${HBASE_VERSION}-hadoop3-bin.tar.gz" \
 && echo "${HBASE_SHA512}  /tmp/hbase.tgz" | sha512sum -c - \
 && tar -xzf /tmp/hbase.tgz -C / \
 && mv "/hbase-${HBASE_VERSION}-hadoop3" /hbase \
 && rm /tmp/hbase.tgz \
 && rm -rf /hbase/docs

ENV HBASE_HOME=/hbase PATH=/hbase/bin:$PATH HBASE_MANAGES_ZK=true
COPY run-hbase.sh /run-hbase.sh

# ZooKeeper, master, region server, web UI: the same ports as the old harisekhon/hbase:1.4 image.
EXPOSE 2181 16000 16010 16020
ENTRYPOINT ["sh", "/run-hbase.sh"]
