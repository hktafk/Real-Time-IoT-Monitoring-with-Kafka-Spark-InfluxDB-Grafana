FROM openjdk:11-jre-slim

# 1. Install OS & Python deps
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
      python3 python3-pip netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

# 2. Copy in just the list of Python requirements
COPY requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt

# 3. Now copy your app code
WORKDIR /app
COPY spark_to_influx.py /app/

ENTRYPOINT ["spark-submit","--master","local[*]","--packages","org.apache.spark:spark-sql-kafka-0-10_2.12:3.2.2","/app/spark_to_influx.py"]
