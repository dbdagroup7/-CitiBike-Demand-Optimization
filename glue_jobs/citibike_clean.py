import sys
import json
import boto3
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.types import *

# ==========================================================
# Job Arguments
# ==========================================================
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'BUCKET',
    'YEAR'
])

BUCKET = args['BUCKET']
YEAR   = args['YEAR']

# ==========================================================
# Spark / Glue Init
# ==========================================================
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

spark.conf.set("spark.sql.shuffle.partitions", "80")

job = Job(glueContext)
job.init(args['JOB_NAME'], args)

print(f"[JOB-1] Starting cleaning job for year={YEAR}")

# ==========================================================
# S3 Paths
# ==========================================================
CITIBIKE_RAW  = f"s3://{BUCKET}/data/raw/citibike/{YEAR}/"
WEATHER_RAW   = f"s3://{BUCKET}/data/raw/weather/{YEAR}_weather.csv"

TMP_CITIBIKE   = f"s3://{BUCKET}/tmp/cleaned/trips/{YEAR}/"
TMP_WEATHER    = f"s3://{BUCKET}/tmp/cleaned/weather/{YEAR}/"

FINAL_CITIBIKE = f"s3://{BUCKET}/data/cleaned/trips/{YEAR}/"
FINAL_WEATHER  = f"s3://{BUCKET}/data/cleaned/weather/{YEAR}/"

METRICS_PATH   = f"s3://{BUCKET}/metrics/job1/{YEAR}/metrics.json"

# ==========================================================
# Explicit Schemas
# ==========================================================
citibike_schema = StructType([
    StructField("ride_id", StringType()),
    StructField("rideable_type", StringType()),
    StructField("started_at", StringType()),
    StructField("ended_at", StringType()),
    StructField("start_station_name", StringType()),
    StructField("start_station_id", StringType()),
    StructField("end_station_name", StringType()),
    StructField("end_station_id", StringType()),
    StructField("start_lat", StringType()),
    StructField("start_lng", StringType()),
    StructField("end_lat", StringType()),
    StructField("end_lng", StringType()),
    StructField("member_casual", StringType())
])

weather_schema = StructType([
    StructField("STATION", StringType()),
    StructField("DATE", StringType()),
    StructField("LATITUDE", StringType()),
    StructField("LONGITUDE", StringType()),
    StructField("ELEVATION", StringType()),
    StructField("NAME", StringType()),
    StructField("TEMP", StringType()),
    StructField("TEMP_ATTRIBUTES", StringType()),
    StructField("DEWP", StringType()),
    StructField("DEWP_ATTRIBUTES", StringType()),
    StructField("SLP", StringType()),
    StructField("SLP_ATTRIBUTES", StringType()),
    StructField("STP", StringType()),
    StructField("STP_ATTRIBUTES", StringType()),
    StructField("VISIB", StringType()),
    StructField("VISIB_ATTRIBUTES", StringType()),
    StructField("WDSP", StringType()),
    StructField("WDSP_ATTRIBUTES", StringType()),
    StructField("MXSPD", StringType()),
    StructField("GUST", StringType()),
    StructField("MAX", StringType()),
    StructField("MAX_ATTRIBUTES", StringType()),
    StructField("MIN", StringType()),
    StructField("MIN_ATTRIBUTES", StringType()),
    StructField("PRCP", StringType()),
    StructField("PRCP_ATTRIBUTES", StringType()),
    StructField("SNDP", StringType()),
    StructField("FRSHTT", StringType())
])

# ==========================================================
# PART A — CLEAN CITIBIKE
# ==========================================================
print("[JOB-1] Reading CitiBike CSVs...")

citibike_df = (
    spark.read
        .schema(citibike_schema)
        .option("header", "true")
        .option("recursiveFileLookup", "true")
        .csv(CITIBIKE_RAW)
)

# ------------------ Cast Types ------------------
citibike_df = (
    citibike_df
        .withColumn("started_at", F.to_timestamp("started_at"))
        .withColumn("ended_at", F.to_timestamp("ended_at"))
        .withColumn("start_lat", F.col("start_lat").cast(DoubleType()))
        .withColumn("start_lng", F.col("start_lng").cast(DoubleType()))
        .withColumn("end_lat", F.col("end_lat").cast(DoubleType()))
        .withColumn("end_lng", F.col("end_lng").cast(DoubleType()))
)

# ------------------ Trip Duration ------------------
citibike_df = citibike_df.withColumn(
    "trip_duration_min",
    (F.unix_timestamp("ended_at") - F.unix_timestamp("started_at")) / 60
)

# ------------------ Filters ------------------
citibike_df = citibike_df.dropDuplicates(["ride_id"])

citibike_df = citibike_df.filter(
    (F.col("trip_duration_min") >= 1) &
    (F.col("trip_duration_min") <= 1440)
)

NYC_LAT_MIN, NYC_LAT_MAX = 40.4774, 40.9176
NYC_LNG_MIN, NYC_LNG_MAX = -74.2591, -73.7004

citibike_df = citibike_df.filter(
    (F.col("start_lat").between(NYC_LAT_MIN, NYC_LAT_MAX)) &
    (F.col("start_lng").between(NYC_LNG_MIN, NYC_LNG_MAX)) &
    (F.col("end_lat").between(NYC_LAT_MIN, NYC_LAT_MAX)) &
    (F.col("end_lng").between(NYC_LNG_MIN, NYC_LNG_MAX))
)

citibike_df = citibike_df.dropna(subset=[
    "ride_id","started_at","ended_at",
    "start_station_name","start_station_id",
    "end_station_name","end_station_id",
    "start_lat","start_lng","end_lat","end_lng"
])

# ------------------ Add trip_date ------------------
citibike_df = citibike_df.withColumn("trip_date", F.to_date("started_at"))

# ------------------ Standardize Column Names ------------------
citibike_df = citibike_df.select([
    F.col(c).alias(c.lower()) for c in citibike_df.columns
])

# ------------------ Coalesce + Write ------------------
citibike_df = citibike_df.coalesce(40)

citibike_df.write \
    .mode("overwrite") \
    .parquet(TMP_CITIBIKE)

# ==========================================================
# PART B — CLEAN WEATHER
# ==========================================================
print("[JOB-1] Reading Weather CSV...")

weather_df = (
    spark.read
        .schema(weather_schema)
        .option("header", "true")
        .csv(WEATHER_RAW)
)

weather_df = (
    weather_df
        .withColumnRenamed("DATE", "trip_date")
        .withColumn("trip_date", F.to_date("trip_date"))
)

weather_numeric_cols = ["TEMP","DEWP","SLP","STP","VISIB","WDSP","MXSPD","GUST","MAX","MIN","PRCP","SNDP"]

for c in weather_numeric_cols:
    weather_df = weather_df.withColumn(c, F.col(c).cast(DoubleType()))

# Sentinel cleanup
for c in weather_numeric_cols:
    weather_df = weather_df.withColumn(
        c,
        F.when(F.col(c) == 999.9, None).otherwise(F.col(c))
    )

weather_df = weather_df.dropDuplicates(["trip_date"])

# Standardize column names
weather_df = weather_df.select([
    F.col(c).alias(c.lower()) for c in weather_df.columns
])

weather_df = weather_df.coalesce(5)

weather_df.write \
    .mode("overwrite") \
    .parquet(TMP_WEATHER)

# ==========================================================
# PART C — DATA QUALITY METRICS
# ==========================================================
metrics = {
    "year": YEAR,
    "citibike_columns": citibike_df.columns,
    "weather_columns": weather_df.columns
}

s3_client = boto3.client("s3")
metrics_key = f"metrics/job1/{YEAR}/metrics.json"

s3_client.put_object(
    Bucket=BUCKET,
    Key=metrics_key,
    Body=json.dumps(metrics, indent=2)
)

print(f"[JOB-1] Metrics written to s3://{BUCKET}/{metrics_key}")

# ==========================================================
# PART D — ATOMIC COMMIT
# ==========================================================
s3_resource = boto3.resource("s3")
bucket_obj = s3_resource.Bucket(BUCKET)

def atomic_move(src_prefix, dest_prefix):
    print(f"[JOB-1] Moving {src_prefix} → {dest_prefix}")
    for obj in bucket_obj.objects.filter(Prefix=src_prefix):
        dest_key = obj.key.replace(src_prefix, dest_prefix, 1)
        bucket_obj.copy({"Bucket": BUCKET, "Key": obj.key}, dest_key)
        obj.delete()

atomic_move(
    src_prefix=f"tmp/cleaned/trips/{YEAR}/",
    dest_prefix=f"data/cleaned/trips/{YEAR}/"
)

atomic_move(
    src_prefix=f"tmp/cleaned/weather/{YEAR}/",
    dest_prefix=f"data/cleaned/weather/{YEAR}/"
)

print("[JOB-1] Atomic commit completed successfully")

# ==========================================================
# Job Complete
# ==========================================================
job.commit()
print("[JOB-1] Job finished successfully")
