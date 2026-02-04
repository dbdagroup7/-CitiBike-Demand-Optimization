import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import *
from pyspark.sql.window import Window
from pyspark.sql.types import StructType, StructField, IntegerType, StringType

# ==========================================================
# Job Arguments
# ==========================================================
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'BUCKET', 'YEAR'])
BUCKET = args['BUCKET'].replace("s3://", "").strip("/")
YEAR = args['YEAR']

# ==========================================================
# Spark / Glue Init
# ==========================================================
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
spark.conf.set("spark.sql.shuffle.partitions", "80")
spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

job = Job(glueContext)
job.init(args['JOB_NAME'], args)

print(f"[GOLD JOB] Starting for YEAR={YEAR}")

# ==========================================================
# Paths
# ==========================================================
SILVER_IN = f"s3://{BUCKET}/data/silver_new/{YEAR}/"
GOLD_FACT = f"s3://{BUCKET}/data/gold/facts/"
GOLD_DIM  = f"s3://{BUCKET}/data/gold/dimensions/"

# ==========================================================
# Read Silver
# ==========================================================
df = spark.read.parquet(SILVER_IN).cache()
total_trips = df.count()

assert "temp" in df.columns, "❌ temp column missing from Silver layer"

print(f"Silver records for {YEAR}: {total_trips:,}")

# ==========================================================
# Create date_key ONCE (CRITICAL FIX)
# ==========================================================
df = df.withColumn(
    "date_key",
    concat(
        lpad(col("year"), 4, "0"),
        lpad(col("month"), 2, "0"),
        lpad(dayofmonth(col("trip_date")), 2, "0")
    ).cast("int")
)

# ==========================================================
# ================= DIMENSIONS ==============================
# ==========================================================

# ---------------- DIM DATE ----------------
dim_date = df.select(
    "date_key",
    "trip_date",
    "year",
    "month",
    "day_of_week",
    "weekend",
    "season"
).dropDuplicates()

dim_date.write.mode("overwrite") \
    .partitionBy("year", "month") \
    .parquet(GOLD_DIM + "dim_date/")

# ---------------- DIM MEMBER --------------
try:
    existing_member = spark.read.parquet(GOLD_DIM + "dim_member/")
    dim_member_raw = df.select("member_casual").union(
        existing_member.select("member_casual")
    ).dropDuplicates()
except:
    dim_member_raw = df.select("member_casual").dropDuplicates()

window_spec = Window.orderBy("member_casual")
dim_member = dim_member_raw.withColumn(
    "member_key",
    row_number().over(window_spec)
).select("member_key", "member_casual")

unknown_member = spark.createDataFrame(
    [(-1, "Unknown")],
    ["member_key", "member_casual"]
)

dim_member = dim_member.union(unknown_member)
dim_member.write.mode("overwrite").parquet(GOLD_DIM + "dim_member/")

# ---------------- DIM STATION -------------
dim_station_new = df.select(
    col("start_station_id").alias("station_id"),
    col("start_station_name").alias("station_name")
).union(
    df.select(
        col("end_station_id").alias("station_id"),
        col("end_station_name").alias("station_name")
    )
).dropDuplicates()

try:
    existing_station = spark.read.parquet(GOLD_DIM + "dim_station/")
    dim_station_raw = dim_station_new.union(
        existing_station.select("station_id", "station_name")
    ).dropDuplicates()
except:
    dim_station_raw = dim_station_new

window_spec = Window.orderBy("station_id")
dim_station = dim_station_raw.withColumn(
    "station_key",
    row_number().over(window_spec)
).select("station_key", "station_id", "station_name")

unknown_station = spark.createDataFrame(
    [(-1, "UNKNOWN", "Unknown Station")],
    ["station_key", "station_id", "station_name"]
)

dim_station = dim_station.union(unknown_station)
dim_station.write.mode("overwrite").parquet(GOLD_DIM + "dim_station/")

# ---------------- DIM BIKE ----------------
try:
    existing_bike = spark.read.parquet(GOLD_DIM + "dim_bike_type/")
    dim_bike_raw = df.select("rideable_type").union(
        existing_bike.select("rideable_type")
    ).dropDuplicates()
except:
    dim_bike_raw = df.select("rideable_type").dropDuplicates()

window_spec = Window.orderBy("rideable_type")
dim_bike = dim_bike_raw.withColumn(
    "bike_key",
    row_number().over(window_spec)
).select("bike_key", "rideable_type")

unknown_bike = spark.createDataFrame(
    [(-1, "Unknown")],
    ["bike_key", "rideable_type"]
)

dim_bike = dim_bike.union(unknown_bike)
dim_bike.write.mode("overwrite").parquet(GOLD_DIM + "dim_bike_type/")

# ---------------- DIM TEMPERATURE ---------
try:
    existing_temp = spark.read.parquet(GOLD_DIM + "dim_temperature/")
    dim_temp_raw = df.select("temp_category").union(
        existing_temp.select("temp_category")
    ).dropDuplicates()
except:
    dim_temp_raw = df.select("temp_category").dropDuplicates()

window_spec = Window.orderBy("temp_category")
dim_temp = dim_temp_raw.withColumn(
    "temp_key",
    row_number().over(window_spec)
).select("temp_key", "temp_category")

unknown_temp = spark.createDataFrame(
    [(-1, "Unknown")],
    ["temp_key", "temp_category"]
)

dim_temp = dim_temp.union(unknown_temp)
dim_temp.write.mode("overwrite").parquet(GOLD_DIM + "dim_temperature/")

# ==========================================================
# ================= FACT TRIPS ==============================
# ==========================================================
dim_member_lu = spark.read.parquet(GOLD_DIM + "dim_member/")
dim_station_lu = spark.read.parquet(GOLD_DIM + "dim_station/")
dim_bike_lu = spark.read.parquet(GOLD_DIM + "dim_bike_type/")
dim_temp_lu = spark.read.parquet(GOLD_DIM + "dim_temperature/")

fact_trips = df \
    .join(dim_member_lu, "member_casual", "left") \
    .join(dim_bike_lu, "rideable_type", "left") \
    .join(dim_temp_lu, "temp_category", "left") \
    .join(
        dim_station_lu.select(
            col("station_id").alias("start_station_id"),
            col("station_key").alias("start_station_key")
        ),
        "start_station_id",
        "left"
    ) \
    .join(
        dim_station_lu.select(
            col("station_id").alias("end_station_id"),
            col("station_key").alias("end_station_key")
        ),
        "end_station_id",
        "left"
    ) \
    .select(
        "ride_id",
        "date_key",
        coalesce("member_key", lit(-1)).alias("member_key"),
        coalesce("bike_key", lit(-1)).alias("bike_key"),
        coalesce("temp_key", lit(-1)).alias("temp_key"),
        coalesce("start_station_key", lit(-1)).alias("start_station_key"),
        coalesce("end_station_key", lit(-1)).alias("end_station_key"),
        "year",
        "month",
        "start_hour",
        "trip_date",
        "trip_distance",
        "trip_duration_min",
        col("temp").alias("temperature"),
        "is_rush_hour",
        "weekend"
    )

fact_trips.write.mode("overwrite") \
    .partitionBy("year", "month") \
    .option("compression", "snappy") \
    .parquet(GOLD_FACT + "fact_trips/")

print(f"✓ fact_trips written ({total_trips:,} rows)")

job.commit()