FROM alpine:latest as downloader
RUN apk add --no-cache wget &&     wget https://jdbc.postgresql.org/download/postgresql-42.7.1.jar -O /postgresql-42.7.1.jar

FROM apache/hive:4.0.0

# Add PostgreSQL JDBC driver
# Using version 42.7.1 which supports SCRAM-SHA-256 authentication
USER root
COPY --from=downloader /postgresql-42.7.1.jar /opt/hive/lib/postgresql-42.7.1.jar
RUN chmod 644 /opt/hive/lib/postgresql-42.7.1.jar

# Install netcat for health checks
RUN apt-get update && apt-get install -y netcat-openbsd && apt-get clean && rm -rf /var/lib/apt/lists/*

USER hive
