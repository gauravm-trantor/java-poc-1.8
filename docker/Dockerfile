FROM eclipse-temurin:8-jre-jammy
RUN apt-get update && apt-get install -y --no-install-recommends curl procps && rm -rf /var/lib/apt/lists/*
# Spark 3.5.8 (EMR 7.14.0's version), Apache's Hadoop 3 build, checked against Apache's published SHA-512.
# Its bundled Hadoop client jars are 3.3.x; on EMR the cluster's own Spark and Hadoop are used.
ARG SPARK_VERSION=3.5.8
ARG SPARK_SHA512=5d5d2e6e111182ee1210d4a46a17ae27107c7ccc70433da0ded3d8197e027f949b00445bb5678ed0c1d5c59f12993d9b9ed12e43686d5aad89a9ec570e93a083
RUN curl -fsSL -o /tmp/spark.tgz "https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz" \
 && echo "${SPARK_SHA512}  /tmp/spark.tgz" | sha512sum -c - \
 && tar -xzf /tmp/spark.tgz -C /opt && rm /tmp/spark.tgz \
 && mv "/opt/spark-${SPARK_VERSION}-bin-hadoop3" /opt/spark
ENV SPARK_HOME=/opt/spark PATH=/opt/spark/bin:$PATH
# hbase-site.xml in Spark's conf dir (on the driver classpath) and in /conf (for the workflow app)
COPY hbase-site.xml /opt/spark/conf/hbase-site.xml
COPY hbase-site.xml /conf/hbase-site.xml
WORKDIR /work
