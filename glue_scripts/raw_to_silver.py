import sys
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType

# ===========================================================
# Job Arguments  
# ===========================================================
args = getResolvedOptions(sys.argv, ['JOB_NAME','BUCKET','YEAR'])

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

# ==========================================================
# Paths
# ==========================================================
CITIBIKE_RAW = f"s3://{BUCKET}/data/raw/citibike/{YEAR}/"
WEATHER_RAW  = f"s3://{BUCKET}/data/raw/weather/{YEAR}_weather.csv"
SILVER_OUT   = f"s3://{BUCKET}/data/silver/{YEAR}/"

# ==========================================================
# Read CitiBike
# ==========================================================
trips = (
    spark.read
        .option("header","true")
        .option("recursiveFileLookup","true")
        .csv(CITIBIKE_RAW)
)

# ----------------------------------------------------------
# Type Casting
# ----------------------------------------------------------
trips = (
    trips
        .withColumn("started_at", F.to_timestamp("started_at"))
        .withColumn("ended_at", F.to_timestamp("ended_at"))
        .withColumn("start_lat", F.col("start_lat").cast(DoubleType()))
        .withColumn("start_lng", F.col("start_lng").cast(DoubleType()))
        .withColumn("end_lat", F.col("end_lat").cast(DoubleType()))
        .withColumn("end_lng", F.col("end_lng").cast(DoubleType()))
)

# ----------------------------------------------------------
# Trip Date & Hour
# ----------------------------------------------------------
trips = (
    trips
        .withColumn("trip_date", F.to_date("started_at"))
        .withColumn("start_hour", F.hour("started_at"))
)

# ----------------------------------------------------------
# Duration (minutes)
# ----------------------------------------------------------
trips = trips.withColumn(
    "trip_duration_min",
    (F.unix_timestamp("ended_at") - F.unix_timestamp("started_at")) / 60
)

# ----------------------------------------------------------
# Drop invalid durations
# ----------------------------------------------------------
trips = trips.filter(
    (F.col("trip_duration_min") > 0) &
    (F.col("trip_duration_min") <= 1440)
)

# ----------------------------------------------------------
# NYC Bounding Box (KEEP)
# ----------------------------------------------------------
trips = trips.filter(
    (F.col("start_lat").between(40.4774, 40.9176)) &
    (F.col("start_lng").between(-74.2591, -73.7004)) &
    (F.col("end_lat").between(40.4774, 40.9176)) &
    (F.col("end_lng").between(-74.2591, -73.7004))
)

# ----------------------------------------------------------
# Remove null critical fields
# ----------------------------------------------------------
trips = trips.dropna(subset=[
    "ride_id","started_at","ended_at",
    "start_station_id","end_station_id"
])

# ----------------------------------------------------------
# Round Trip Flag
# ----------------------------------------------------------
trips = trips.withColumn(
    "is_round_trip",
    F.when(
        (F.col("start_station_id") == F.col("end_station_id")) &
        (F.col("start_lat") == F.col("end_lat")) &
        (F.col("start_lng") == F.col("end_lng")),
        1
    ).otherwise(0)
)

# ==========================================================
# Read Weather
# ==========================================================
weather = (
    spark.read
        .option("header","true")
        .csv(WEATHER_RAW)
        .withColumnRenamed("DATE","raw_date")
        .withColumn(
            "trip_date",
            F.to_date("raw_date", "dd-MM-yyyy")
        )
)

for c in ["TEMP","VISIB","WDSP","PRCP","SNDP"]:
    weather = weather.withColumn(c, F.col(c).cast(DoubleType()))

for c in ["TEMP","VISIB","WDSP","PRCP","SNDP"]:
    weather = weather.withColumn(
        c,
        F.when(F.col(c) == 999.9, 0.0).otherwise(F.col(c))
    )

weather = (
    weather
        .select("trip_date","TEMP","VISIB","WDSP","PRCP","SNDP","FRSHTT")
        .dropDuplicates(["trip_date"])
)

# ==========================================================
# Join Trips + Weather
# ==========================================================
df = trips.join(weather, "trip_date", "left")

# ==========================================================
# Distance (Haversine — KEEP temp columns)
# ==========================================================
R = 3958.8

df = (
    df
        .withColumn("lat1", F.radians("start_lat"))
        .withColumn("lon1", F.radians("start_lng"))
        .withColumn("lat2", F.radians("end_lat"))
        .withColumn("lon2", F.radians("end_lng"))
)

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
# Temporal Features
# ==========================================================
df = (
    df
        .withColumn("day_of_week", F.date_format("trip_date","EEEE"))
        .withColumn("month", F.month("trip_date"))
        .withColumn("year", F.year("trip_date"))
)

df = df.withColumn(
    "season",
    F.when(F.col("month").isin([12,1,2]),"Winter")
     .when(F.col("month").isin([3,4,5]),"Spring")
     .when(F.col("month").isin([6,7,8]),"Summer")
     .otherwise("Fall")
)

df = (
    df
        .withColumn("weekend", F.dayofweek("trip_date").isin([1,7]))
        .withColumn("is_rush_hour", F.col("start_hour").isin([7,8,9,16,17,18]))
)

HOLIDAYS = [f"{YEAR}-01-01", f"{YEAR}-07-04", f"{YEAR}-12-25"]

df = df.withColumn(
    "is_holiday",
    F.col("trip_date").cast("string").isin(HOLIDAYS)
)

# ==========================================================
# Weather Flags
# ==========================================================
df = df.fillna({"FRSHTT":"000000"})

df = (
    df
        .withColumn("is_fog",     F.substring("FRSHTT",1,1).cast("int"))
        .withColumn("is_rain",    F.substring("FRSHTT",2,1).cast("int"))
        .withColumn("is_snow",    F.substring("FRSHTT",3,1).cast("int"))
        .withColumn("is_hail",    F.substring("FRSHTT",4,1).cast("int"))
        .withColumn("is_thunder", F.substring("FRSHTT",5,1).cast("int"))
        .withColumn("is_tornado", F.substring("FRSHTT",6,1).cast("int"))
        .drop("FRSHTT")
)

# ----------------------------------------------------------
# Rename weather columns (Athena fix)
# ----------------------------------------------------------
df = (
    df
        .withColumnRenamed("TEMP","temp")
        .withColumnRenamed("VISIB","visib")
        .withColumnRenamed("WDSP","wdsp")
        .withColumnRenamed("PRCP","prcp")
        .withColumnRenamed("SNDP","sndp")
)

# ==========================================================
# Categories
# ==========================================================
df = (
    df
        .withColumn(
            "temp_category",
            F.when(F.col("temp") >= 75,"Warm")
             .when(F.col("temp") >= 55,"Moderate")
             .otherwise("Cool")
        )
        .withColumn(
            "prcp_category",
            F.when(F.col("prcp") == 0,"No Rain")
             .when(F.col("prcp") <= 0.1,"Light")
             .when(F.col("prcp") <= 0.3,"Moderate")
             .otherwise("Heavy")
        )
)

# ==========================================================
# FINAL SCHEMA LOCK (CRITICAL)
# ==========================================================
df = df.select(
    "ride_id","rideable_type","member_casual",
    "started_at","ended_at","trip_date","start_hour",
    "start_station_id","start_station_name",
    "end_station_id","end_station_name",
    "start_lat","start_lng","end_lat","end_lng",
    "trip_duration_min","trip_distance",
    "is_round_trip","weekend","is_rush_hour","is_holiday",
    "day_of_week","month","year","season",
    "temp","visib","wdsp","prcp","sndp",
    "is_fog","is_rain","is_snow","is_hail","is_thunder","is_tornado",
    "temp_category","prcp_category"
)

# ==========================================================
# Write Silver
# ==========================================================
df.coalesce(80).write.mode("overwrite").parquet(SILVER_OUT)

job.commit()
