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

print(f"[JOB-2] Starting enrichment job for year={YEAR}")

# ==========================================================
# S3 Paths
# ==========================================================
CITIBIKE_CLEAN = f"s3://{BUCKET}/data/cleaned/trips/{YEAR}/"
WEATHER_CLEAN  = f"s3://{BUCKET}/data/cleaned/weather/{YEAR}/"

FINAL_CURATED  = f"s3://{BUCKET}/data/curated/citibike_enriched/{YEAR}/"

# ==========================================================
# Read Clean Data
# ==========================================================
print("[JOB-2] Reading cleaned datasets...")

trips_df   = spark.read.parquet(CITIBIKE_CLEAN)
weather_df = spark.read.parquet(WEATHER_CLEAN)

# Broadcast weather (small dimension table)
weather_df = F.broadcast(weather_df)

# ==========================================================
# Join
# ==========================================================
print("[JOB-2] Joining trips with weather...")

df = trips_df.join(weather_df, on="trip_date", how="left")

# ==========================================================
# Drop Unused Weather Columns
# ==========================================================
drop_cols = [
    "station","latitude","longitude","elevation","name",
    "temp_attributes","dewp_attributes","slp_attributes",
    "stp_attributes","visib_attributes","wdsp_attributes",
    "max_attributes","min_attributes","prcp_attributes",
    "mxspd","gust","slp","stp"
]

for c in drop_cols:
    if c in df.columns:
        df = df.drop(c)

# ==========================================================
# Distance Calculation (Haversine in miles)
# ==========================================================
print("[JOB-2] Computing trip distance...")

R = 3958.8

df = df.withColumn("lat1", F.radians("start_lat")) \
       .withColumn("lon1", F.radians("start_lng")) \
       .withColumn("lat2", F.radians("end_lat")) \
       .withColumn("lon2", F.radians("end_lng"))

df = df.withColumn(
    "trip_distance",
    R * 2 * F.asin(F.sqrt(
        F.pow(F.sin((F.col("lat2") - F.col("lat1")) / 2), 2) +
        F.cos("lat1") * F.cos("lat2") *
        F.pow(F.sin((F.col("lon2") - F.col("lon1")) / 2), 2)
    ))
)

df = df.withColumn("trip_distance", F.round("trip_distance", 2))
df = df.drop("lat1","lon1","lat2","lon2")

# ==========================================================
# Split Timestamps
# ==========================================================
df = (
    df
    .withColumn("start_date", F.to_date("started_at"))
    .withColumn("start_time", F.date_format("started_at", "HH:mm:ss"))
    .withColumn("end_date", F.to_date("ended_at"))
    .withColumn("end_time", F.date_format("ended_at", "HH:mm:ss"))
)

# ==========================================================
# Temporal Features
# ==========================================================
print("[JOB-2] Creating temporal features...")

df = (
    df
    .withColumn("start_hour", F.hour("started_at"))
    .withColumn("day_of_week", F.date_format("trip_date", "E"))
    .withColumn("month", F.month("trip_date"))
    .withColumn("year", F.year("trip_date"))
)

df = df.withColumn(
    "season",
    F.when(F.col("month").isin([12,1,2]), "Winter")
     .when(F.col("month").isin([3,4,5]), "Spring")
     .when(F.col("month").isin([6,7,8]), "Summer")
     .otherwise("Fall")
)

# ==========================================================
# Rush Hour Flag
# ==========================================================
df = df.withColumn(
    "is_rush_hour",
    F.when(
        (F.col("start_hour").between(7,9)) |
        (F.col("start_hour").between(16,19)),
        True
    ).otherwise(False)
)

# ==========================================================
# Round Trip Flag
# ==========================================================
df = df.withColumn(
    "is_round_trip",
    F.col("start_station_id") == F.col("end_station_id")
)

# ==========================================================
# Temperature Category
# ==========================================================
df = df.withColumn(
    "temp_category",
    F.when(F.col("temp") < 50, "cool")
     .when(F.col("temp") <= 75, "moderate")
     .otherwise("warm")
)

# ==========================================================
# Precipitation Category
# ==========================================================
df = df.withColumn(
    "prcp_category",
    F.when(F.col("prcp") == 0, "no rain")
     .when(F.col("prcp") < 0.1, "light")
     .when(F.col("prcp") < 0.5, "moderate")
     .otherwise("heavy")
)

# ==========================================================
# Decode FRSHTT Flags
# ==========================================================
print("[JOB-2] Decoding weather flags...")

df = df.fillna({"frshtt": "000000"})

df = (
    df
    .withColumn("is_fog",     F.substring("frshtt", 1, 1).cast("int"))
    .withColumn("is_rain",    F.substring("frshtt", 2, 1).cast("int"))
    .withColumn("is_snow",    F.substring("frshtt", 3, 1).cast("int"))
    .withColumn("is_hail",    F.substring("frshtt", 4, 1).cast("int"))
    .withColumn("is_thunder", F.substring("frshtt", 5, 1).cast("int"))
    .withColumn("is_tornado", F.substring("frshtt", 6, 1).cast("int"))
    .drop("frshtt")
)

# ==========================================================
# Trip Speed
# ==========================================================
df = df.withColumn(
    "trip_speed_mph",
    F.round(F.col("trip_distance") / (F.col("trip_duration_min") / 60), 2)
)

# ==========================================================
# Final Quality Filters
# ==========================================================
print("[JOB-2] Applying final quality filters...")

df = df.filter(
    (F.col("trip_distance") >= 0) &
    (F.col("trip_duration_min") > 0) &
    (F.col("trip_duration_min") < 1440) &
    (F.col("trip_speed_mph") <= 40)
)

# ==========================================================
# Drop Raw Timestamps
# ==========================================================
df = df.drop("started_at", "ended_at")

# ==========================================================
# PATCH: Recompute weekend flag safely (BOOLEAN)
# ==========================================================

df = df.withColumn(
    "weekend",
    F.when(F.dayofweek("trip_date").isin([1, 7]), F.lit(True))
     .otherwise(F.lit(False))
)

# ==========================================================
# PATCH: Recompute holiday flag safely
# ==========================================================

HOLIDAYS = [
    f"{YEAR}-01-01",   # New Year
    f"{YEAR}-07-04",   # Independence Day
    f"{YEAR}-12-25"    # Christmas
]

holiday_dates = [F.to_date(F.lit(d)) for d in HOLIDAYS]

df = df.withColumn(
    "is_holiday",
    F.col("trip_date").isin(holiday_dates)
)

# ==========================================================
# PATCH: Safe weather null handling
# ==========================================================

df = df.fillna({
    "prcp": 0.0,
    "sndp": 0.0,

    "is_fog": 0,
    "is_rain": 0,
    "is_snow": 0,
    "is_hail": 0,
    "is_thunder": 0,
    "is_tornado": 0
})

# ==========================================================
# Drop rows with missing weather data (unmatched join days)
# ==========================================================
print("[JOB-2] Dropping rows with missing weather data...")

df = df.filter(
    F.col("temp").isNotNull() &
    F.col("visib").isNotNull() &
    F.col("wdsp").isNotNull()
)

# ==========================================================
# Column Ordering
# ==========================================================
preferred_order = [
    "ride_id","rideable_type","member_casual",
    "start_date","start_time","end_date","end_time","trip_date",
    "start_hour","day_of_week","month","year","season","is_rush_hour",
    "weekend","is_holiday","is_round_trip",
    "start_station_name","start_station_id",
    "end_station_name","end_station_id",
    "start_lat","start_lng","end_lat","end_lng",
    "trip_distance","trip_duration_min","trip_speed_mph",
    "temp","temp_category","visib","wdsp","max","min","prcp","prcp_category","sndp",
    "is_fog","is_rain","is_snow","is_hail","is_thunder","is_tornado"
]

existing_cols = [c for c in preferred_order if c in df.columns]
df = df.select(*existing_cols)

# ==========================================================
# Coalesce + Write
# ==========================================================
print("[JOB-2] Writing curated dataset...")

df = df.coalesce(60)

df.write \
    .mode("overwrite") \
    .parquet(FINAL_CURATED)

print(f"[JOB-2] Output written to: {FINAL_CURATED}")

# ==========================================================
# Job Complete
# ==========================================================
job.commit()
print("[JOB-2] Job completed successfully")
