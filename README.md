# 🚲 CitiBike Demand Optimization

An end-to-end cloud-based data analytics and visualization platform built using NYC CitiBike trip data integrated with historical weather data to analyze demand patterns and weather impact on ridership.

---

## Project Overview

The CitiBike Demand Optimization project focuses on building an end-to-end, cloud-based data analytics and visualization platform using NYC CitiBike trip data integrated with historical weather data. The objective is to analyze bike usage patterns, understand the impact of weather on ridership, and enable data-driven demand optimization through scalable analytics.

The project follows a modern serverless data architecture on AWS, leveraging distributed ETL processing, optimized storage formats, query-on-demand analytics, and BI dashboards.

---

## Services, Tools, and Technologies Used

### Cloud & Data Engineering

**Amazon S3**  
Amazon S3 is a highly scalable and durable object storage service used to store large volumes of data.  
In this project, S3 stores raw CitiBike and weather datasets and also holds cleaned, transformed, and partitioned Parquet data for analytics.

**AWS Glue**  
AWS Glue is a fully managed serverless service for large-scale data extraction, transformation, and loading.  
In this project, Glue runs PySpark jobs to clean raw data, merge datasets, perform feature engineering, and generate aggregated analytical tables.

**Amazon Athena**  
Amazon Athena is a serverless, interactive query service that allows SQL queries directly on data stored in S3.  
In this project, Athena is used to query curated, partitioned datasets efficiently without data movement.

**AWS IAM**  
AWS Identity and Access Management (IAM) enables secure authentication and fine-grained authorization for AWS resources.  
In this project, IAM roles and policies control access to S3, Glue, Athena, and Power BI connectivity.

### Analytics & Visualization
- Power BI – Interactive dashboards and reporting  
- Athena ODBC Connector – Power BI integration  

### Development & DevOps
- Python (PySpark)  
- SQL  
- Git & GitHub – Version control and collaboration  
- GitHub Actions – CI/CD pipelines  
- Jira – Project timeline and task management  

---

## 1. Datasets Used

This project uses two datasets to analyze CitiBike demand and its dependency on weather conditions in New York City.

### CitiBike NYC Trip Data
- **Source:** NYC CitiBike System Data  
- **Link:** https://citibikenyc.com/system-data  
- **Description:** Ride-level data containing trip times, station details, bike type, and user category  
- **Format:** CSV (monthly historical data)

### Weather Data (NOAA)
- **Source:** NOAA – Global Summary of the Day  
- **Link:** https://www.ncei.noaa.gov/data/global-summary-of-the-day/archive/  
- **Description:** Daily weather data including temperature, precipitation, wind speed, and weather events  
- **Format:** CSV

---

## 2. Exploratory Data Analysis (EDA) – Key Findings

Based on the initial exploratory analysis, the following observations were made:

### Dataset Size & Structure
- **Total Records:** 29.48 Million ride records  
- **Total Columns:** 41 columns after merging CitiBike and weather datasets  
- **File Size:** 1.65 GBs, confirming large-scale historical data  

---

### Time Coverage
- **Ride Data Period:** Covers all months from January to August 2025  
- **Weather Data Granularity:** Daily observations aligned with ride dates  
- Data shows continuous temporal coverage with no major gaps in dates  

---

### User & Bike Distribution
- **User Type:**  
  - Member users contribute the majority of rides  
  - Casual users form a smaller but significant share  
- **Bike Type:**  
  - Classic bikes dominate overall usage  
  - Electric bikes represent a smaller proportion  

---

### Trip Duration Analysis
- **Average Trip Duration:** ~10–15 minutes  
- **Majority of Trips:** Less than 30 minutes  
- **Outliers:**  
  - Very long trips (> 24 hours) detected  
  - These were treated as anomalies during transformation  

---

### Station-Level Observations
- A limited number of stations contribute to a high volume of total trips  
- Start and end station distributions indicate demand hotspots in central locations  

---

### Weather Data Observations
- **Temperature Range:** Falls within expected seasonal NYC ranges  
- **Precipitation:**  
  - Most days have low or zero precipitation  
  - Heavy precipitation events are rare  
- **Wind Speed:** Mostly low to moderate values  

---

### Weather Event Indicators
- Columns such as `FRSHTT` indicate:  
  - Rain events occur more frequently than snow or thunder  
  - Snow and thunder events are relatively rare  

---

### Data Quality Findings
- **Missing Values:**  
  - Minimal nulls in core ride fields  
  - Weather columns contain placeholder values (e.g., `999.9`) indicating missing measurements  
- **Duplicates:**  
  - Duplicate ride records were negligible  
- **Invalid Values:**  
  - Some unrealistic trip durations and distances were identified  

---

### Key EDA Conclusion
The dataset is large, well-structured, and suitable for analytics, with a small number of anomalies and missing weather values.  
EDA findings directly influenced data cleaning rules, feature engineering logic, outlier handling, and aggregation strategies used in the ETL pipeline.

---

## 3. Project Architecture

<p align="center">
  <img src="images/architecture.png" width="850"/>
</p>
<p align="center">
  <b>Figure:</b> End-to-end architecture of the CitiBike Demand Optimization pipeline
</p>

---

## 4. Data Processing Using AWS Glue (Silver Layer)

This stage processes raw CitiBike and weather data using AWS Glue (PySpark) and prepares an enriched, analytics-ready dataset.

### 4.1 Data Cleaning
- Converted timestamps, latitude, longitude, and numeric fields to correct data types  
- Removed records with invalid or missing critical values  
- Filtered trips with unrealistic durations  
- Restricted trips to valid New York City geographic boundaries  
- Handled missing and sentinel weather values  

---

### 4.2 Data Merging
- Integrated CitiBike trip data with daily weather data using `trip_date`  
- Retained only records with valid and usable weather observations  
- Created a unified dataset combining ride behavior with environmental conditions  

---

### 4.3 Data Transformation & Feature Engineering
- Calculated trip duration and trip distance (Haversine formula)  
- Derived temporal features: day of week, month, year, season, start hour  
- Generated analytical flags: weekend, rush hour, holiday, round trip  
- Created weather event indicators (rain, snow, fog, thunder, hail)  
- Categorized temperature and precipitation into business-friendly groups  

---

The final output is stored in Amazon S3 as Parquet files, partitioned by year and month.

---

## 5. Initial Merged Data Dictionary (Pre-Transformation)

| Sr No | Column Name | Description | Data Type | Sample Values |
|-----|------------|-------------|----------|---------------|
| 1 | ride_id | Unique identifier for each ride | String | BF31E940F7D80958 |
| 2 | rideable_type | Type of bike used | String | electric_bike, classic_bike |
| 3 | started_at | Ride start timestamp | Datetime | 2024-07-11 08:45:00 |
| 4 | ended_at | Ride end timestamp | Datetime | 2024-07-11 09:05:00 |
| 5 | start_station_name | Start station name | String | N 6 St & Bedford Ave |
| 6 | start_station_id | Start station ID | String | 5379.1 |
| 7 | end_station_name | End station name | String | Broadway & Berry St |
| 8 | end_station_id | End station ID | String | 5164.05 |
| 9 | start_lat | Start latitude | Float | 40.71745 |
| 10 | start_lng | Start longitude | Float | -73.95850 |
| 11 | end_lat | End latitude | Float | 40.71036 |
| 12 | end_lng | End longitude | Float | -73.96530 |
| 13 | member_casual | Rider membership type | String | member, casual |
| 14 | trip_date | Ride date | Date | 2024-07-11 |
| 15 | station | Weather station number | String | 72505394728 |
| 16 | latitude | Weather station latitude | Float | 40.77898 |
| 17 | longitude | Weather station longitude | Float | -73.96925 |
| 18 | elevation | Station elevation (meters) | Float | 42.7 |
| 19 | name | Station name | String | NY CITY CENTRAL PARK |
| 20 | TEMP | Mean temperature (°F) | Float | 76.2 |
| 36 | PRCP | Precipitation | Float | 0.18 |
| 39 | FRSHTT | Weather event flags | String | 010010 |

---

## 6. Gold Layer – Aggregation Tables for Analytics

In this stage, enriched Silver-layer data is aggregated into multiple Gold-layer tables optimized for analytics and dashboard consumption.

### 6.1 Fact Table Creation
- Central fact table with ride-level analytical attributes  
- Partitioned by year and month  

### 6.2 Time-Based Aggregations
- Hourly aggregation for peak demand  
- Daily aggregation for trend analysis  

### 6.3 Bike & Weather-Based Aggregations
- Bike type-based aggregation  
- Temperature category-based aggregation  

### 6.4 Station-Level Aggregation
- Trips started and ended per station  
- Total station activity  

### 6.5 Summary Metrics
- Total trips  
- Average trip distance  
- Average trip duration  
- Average temperature  
- Peak usage hour  

All Gold-layer outputs are stored using a run-based (`run_id`) strategy.

---

## 7. Key Performance Indicators (KPIs) & Dashboard Charts

### KPI 1: Total Trips
Measures overall ride demand.

**Supporting Charts:**  
- Total Trips by Bike Type  
- Member vs Casual Trip Share  

### KPI 2: Average Trip Distance
Analyzes typical ride distance.

**Supporting Charts:**  
- Station Utilization Rate by Bike Type  
- Station Imbalance Analysis  

### KPI 3: Average Trip Duration
Evaluates average ride time.

**Supporting Charts:**  
- Trips by Temperature  

### KPI 4: Peak Usage Hour
Identifies busiest hour of the day.

**Supporting Charts:**  
- Total Trips by Start Hour  

### KPI 5: Rush Hour Usage Ratio
Analyzes rush hour demand.

**Supporting Charts:**  
- Rush Hour vs Non-Rush Hour Usage by User Type  

### KPI 6: Weekend Usage Ratio
Compares weekday and weekend usage.

**Supporting Charts:**  
- Weekend Usage Distribution  

---

## 8. Infrastructure as Code (Terraform) & CI/CD Implementation

### Infrastructure as Code (Terraform)
- Provisioned S3 buckets for raw, silver, and gold layers  
- Managed IAM roles for Glue and Athena  

### CI/CD Pipeline (GitHub Actions)
- Automated Glue job deployments  
- Triggered pipelines on code updates  

Terraform and CI/CD together enable a fully automated, reproducible, and production-ready data engineering workflow.
