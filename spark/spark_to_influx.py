# spark_to_influx.py
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import (
    StructType, StructField,
    MapType, StringType,
    DoubleType, LongType
)
from influxdb_client import InfluxDBClient, Point, WritePrecision

# —— InfluxDB config via env vars —— 
INFLUX_URL    = os.getenv("INFLUX_URL",    "http://influxdb:8086")
INFLUX_TOKEN  = os.getenv("INFLUX_TOKEN",  "admintoken")
INFLUX_ORG    = os.getenv("INFLUX_ORG",    "myorg")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "iot_data")

# Initialize InfluxDB client
influx    = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx.write_api()

# Build SparkSession
spark = (
    SparkSession.builder
                .appName("ModbusToInflux")
                .config("spark.sql.shuffle.partitions", "1")
                .getOrCreate()
)

# JSON schema
schema = StructType([
    StructField("name",      StringType()),
    StructField("tags",      MapType(StringType(), StringType())),
    StructField("fields",    MapType(StringType(), DoubleType())),
    StructField("timestamp", LongType()),       # <-- keep as LongType
])

# Read from Kafka
raw = (
    spark.readStream
         .format("kafka")
         .option("kafka.bootstrap.servers", "kafka:9092")
         .option("subscribe",               "modbus_sensor1")
         .option("startingOffsets",         "latest")
         .load()
)

# Parse & flatten
parsed = (
    raw
    .selectExpr("CAST(value AS STRING) AS json_str")
    .select(from_json(col("json_str"), schema).alias("j"))
    .select(
        col("j.tags.device_id").alias("device_id"),  
        col("j.fields.V_L1").alias("V_L1"),
        col("j.fields.I_L1").alias("I_L1"),
        col("j.fields.VA_L1").alias("VA_L1"),
        col("j.fields.P_L1").alias("P_L1"),          
        col("j.timestamp").cast(LongType()).alias("ts")
    )
)

def foreach_batch(batch_df, batch_id):
    pts = []
    for row in batch_df.toLocalIterator():
        # row.ts is now int, so Influx will accept it
        pts.append(
            Point("modbus_metrics")
              .tag("device_id", row.device_id)
              .field("V_L1", row.V_L1)
              .field("I_L1", row.I_L1)
              .field("VA_L1", row.VA_L1)
              .field("P_L1", row.P_L1)
              .time(row.ts, WritePrecision.S)
        )

    if pts:
        print(f">>> Batch {batch_id}: writing {len(pts)} points")
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=pts)

# Start streaming
(
    parsed.writeStream
          .foreachBatch(foreach_batch)
          .outputMode("append")
          .start()
          .awaitTermination()
)
