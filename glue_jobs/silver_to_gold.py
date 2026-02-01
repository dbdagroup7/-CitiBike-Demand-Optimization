import sys
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from awsglue.job import Job
from pyspark.sql import functions as F

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
# Spark Init
# ==========================================================
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

spark.conf.set("spark.sql.shuffle.partitions", "80")

job = Job(glueContext)
job.init(args['JOB_NAME'], args)

print(f"[JOB-3] Starting GOLD aggregation job for year={YEAR}")

# ==========================================================
# S3 Paths (UPDATED – Job 2)
# ==========================================================

SILVER_PATH = f"s3://{BUCKET}/data/silver/citibike/{YEAR}/"

GOLD_BASE = f"s3://{BUCKET}/data/gold/citibike/{YEAR}"

DIM_CALENDAR_PATH = f"{GOLD_BASE}/dim_calendar/"

KPI_PATH               = f"{GOLD_BASE}/gold_kpi_cards/"
MEMBER_SHARE_PATH      = f"{GOLD_BASE}/gold_member_casual_share/"
BIKE_TYPE_PATH         = f"{GOLD_BASE}/gold_trips_by_bike_type/"
WEEKEND_USER_PATH      = f"{GOLD_BASE}/gold_weekend_weekday_user/"
RUSH_HOUR_USER_PATH    = f"{GOLD_BASE}/gold_rush_hour_user/"
TRIPS_BY_HOUR_PATH     = f"{GOLD_BASE}/gold_trips_by_hour/"
TEMP_PATTERN_PATH      = f"{GOLD_BASE}/gold_trips_by_temperature/"
TOP_STATIONS_PATH      = f"{GOLD_BASE}/gold_top_start_stations/"
STATION_IMBALANCE_PATH = f"{GOLD_BASE}/gold_station_imbalance/"
DAILY_AGG_PATH         = f"{GOLD_BASE}/gold_daily_aggregates/"

# ==========================================================
# Read Silver Layer
# ==========================================================
print("[JOB-3] Reading silver dataset...")
df = spark.read.parquet(SILVER_PATH).cache()

# ==========================================================
# Boolean → Integer Casting (FIX FOR AGGREGATIONS)
# ==========================================================
print("[JOB-3] Casting boolean flags to integers...")

df = (
    df
        .withColumn("weekend", F.col("weekend").cast("int"))
        .withColumn("is_rush_hour", F.col("is_rush_hour").cast("int"))
        .withColumn("is_holiday", F.col("is_holiday").cast("int"))
        .withColumn("is_round_trip", F.col("is_round_trip").cast("int"))
)

# ==========================================================
# DIMENSION: Calendar
# ==========================================================
print("[JOB-3] Building calendar dimension...")

dim_calendar = (
    df
      .select("trip_date", "year", "month", "weekend")
      .dropDuplicates()
      .withColumn("month_name", F.date_format("trip_date", "MMMM"))
      .withColumn(
          "day_type",
          F.when(F.col("weekend") == 1, "Weekend").otherwise("Weekday")
      )
)

dim_calendar.write.mode("overwrite").parquet(DIM_CALENDAR_PATH)

# ==========================================================
# KPI CARDS
# ==========================================================
print("[JOB-3] Generating KPI cards...")

kpi_df = df.agg(
    F.avg("trip_distance").alias("avg_distance_km"),
    F.avg("trip_duration_min").alias("avg_trip_duration_minutes"),
    F.expr("percentile_approx(start_hour, 0.5)").alias("peak_usage_hour"),
    (F.sum(F.col("is_rush_hour")) / F.count("*") * 100).alias("rush_hour_usage_pct"),
    (F.sum(F.col("weekend").cast("int")) / F.count("*") * 100).alias("weekend_demand_pct"),
    F.avg("temp").alias("avg_temp_f"),
    F.count("*").alias("total_trips"),
    F.countDistinct("start_station_id").alias("unique_stations")
)

kpi_df.coalesce(1).write.mode("overwrite").parquet(KPI_PATH)

# ==========================================================
# MEMBER VS CASUAL SHARE  (FIXED)
# ==========================================================

total_trips_value = df.count()

member_share = (
    df.groupBy("member_casual")
      .agg(F.count("*").alias("total_trips"))
      .withColumn(
          "trip_share_pct",
          (F.col("total_trips") / F.lit(total_trips_value)) * 100
      )
)

member_share.coalesce(5).write.mode("overwrite").parquet(MEMBER_SHARE_PATH)

# ==========================================================
# TRIPS BY BIKE TYPE
# ==========================================================
bike_type = (
    df.groupBy("rideable_type")
      .agg(F.count("*").alias("total_trips"))
)

bike_type.coalesce(5).write.mode("overwrite").parquet(BIKE_TYPE_PATH)

# ==========================================================
# WEEKEND VS WEEKDAY BY USER
# ==========================================================
weekend_user = (
    df.groupBy("member_casual", "weekend")
      .agg(F.count("*").alias("total_trips"))
      .withColumn(
          "day_type",
          F.when(F.col("weekend") == 1, "Weekend").otherwise("Weekday")
      )
)

weekend_user.coalesce(10).write.mode("overwrite").parquet(WEEKEND_USER_PATH)

# ==========================================================
# RUSH HOUR BY USER
# ==========================================================
rush_user = (
    df.groupBy("member_casual", "is_rush_hour")
      .agg(F.count("*").alias("total_trips"))
      .withColumn(
          "rush_hour_type",
          F.when(F.col("is_rush_hour") == 1, "Rush Hour").otherwise("Non Rush")
      )
)

rush_user.coalesce(10).write.mode("overwrite").parquet(RUSH_HOUR_USER_PATH)

# ==========================================================
# TRIPS BY HOUR
# ==========================================================
trips_by_hour = (
    df.groupBy("trip_date", "start_hour")
      .agg(
          F.count("*").alias("total_trips"),
          F.avg("trip_duration_min").alias("avg_duration_minutes")
      )
)

trips_by_hour.coalesce(20).write.mode("overwrite").parquet(TRIPS_BY_HOUR_PATH)

# ==========================================================
# TRIPS BY TEMPERATURE CATEGORY
# ==========================================================
temp_pattern = (
    df.groupBy("trip_date", "temp_category")
      .agg(
          F.count("*").alias("total_trips"),
          F.avg("trip_duration_min").alias("avg_duration_minutes"),
          F.avg("trip_distance").alias("avg_distance_km")
      )
)

temp_pattern.coalesce(20).write.mode("overwrite").parquet(TEMP_PATTERN_PATH)

# ==========================================================
# TOP START STATIONS
# ==========================================================
top_stations = (
    df.groupBy("trip_date", "start_station_id", "start_station_name")
      .agg(
          F.count("*").alias("total_trips"),
          F.avg("trip_duration_min").alias("avg_duration_minutes"),
          F.avg("trip_distance").alias("avg_distance_km")
      )
)

top_stations.coalesce(30).write.mode("overwrite").parquet(TOP_STATIONS_PATH)

# ==========================================================
# STATION IMBALANCE
# ==========================================================
outflow = (
    df.groupBy("trip_date", "start_station_id", "start_station_name")
      .agg(F.count("*").alias("outflow"))
)

inflow = (
    df.groupBy("trip_date", "end_station_id", "end_station_name")
      .agg(F.count("*").alias("inflow"))
      .withColumnRenamed("end_station_id", "start_station_id")
      .withColumnRenamed("end_station_name", "start_station_name")
)

station_balance = (
    outflow.join(
        inflow,
        ["start_station_id", "start_station_name", "trip_date"],
        "outer"
    )
    .fillna(0)
    .withColumn("net_flow", F.col("inflow") - F.col("outflow"))
    .withColumn(
        "imbalance_index",
        F.when((F.col("inflow") + F.col("outflow")) == 0, 0)
         .otherwise(F.col("net_flow") / (F.col("inflow") + F.col("outflow")))
    )
)

station_balance.coalesce(30).write.mode("overwrite").parquet(STATION_IMBALANCE_PATH)

# ==========================================================
# DAILY AGGREGATES
# ==========================================================
daily_agg = (
    df.groupBy("trip_date")
      .agg(
          F.count("*").alias("total_trips"),
          F.avg("trip_duration_min").alias("avg_duration_minutes"),
          F.avg("trip_distance").alias("avg_distance_km"),
          F.avg("temp").alias("avg_temp_f"),
          F.sum("prcp").alias("total_precipitation")
      )
)

daily_agg.coalesce(20).write.mode("overwrite").parquet(DAILY_AGG_PATH)

# ==========================================================
# Job Complete
# ==========================================================
job.commit()
print("[JOB-3] GOLD layer generation completed successfully.")
