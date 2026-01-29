# 🚲 CitiBike Demand Optimization

An end-to-end cloud-based data analytics and visualization platform built using NYC CitiBike trip data integrated with historical weather data to analyze demand patterns and weather impact on ridership.

---

## 1. Project Overview

The CitiBike Demand Optimization project focuses on building an end-to-end, cloud-based data analytics and visualization platform using NYC CitiBike trip data integrated with historical weather data. The objective is to analyze bike usage patterns, understand the impact of weather on ridership, and enable data-driven demand optimization through scalable analytics.

The project follows a modern serverless data architecture on AWS, leveraging distributed ETL processing, optimized storage formats, query-on-demand analytics, and BI dashboards.

---

## 2. High-Level Architecture & Execution Flow

1. Raw CitiBike trip data and historical weather data are ingested from multiple sources.  
2. Raw datasets are stored in Amazon S3 (raw layer).  
3. AWS Glue Job 1 performs data cleaning and standardization.  
4. AWS Glue Job 2 merges CitiBike and weather datasets and applies feature engineering and transformations.  
5. AWS Glue Job 3 aggregates data for analytical use cases.  
6. Cleaned and partitioned datasets are written back to Amazon S3 (processed layer).  
7. Amazon Athena is used to query curated datasets directly from S3.  
8. Power BI connects to Athena via ODBC to build interactive dashboards.  
9. GitHub Actions manages CI/CD for ETL jobs and workflow updates.  
10. Infrastructure is managed using Infrastructure as Code (IaC).

---

## 3. Services, Tools, and Technologies Used

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

## 4. Data Ingestion Layer

### CitiBike Trip Data
- Source: NYC CitiBike public trip history datasets  
- Format: CSV  
- Frequency: Monthly historical files  

### Weather Data
- Source: NOAA historical weather datasets  
- Format: CSV  
- Granularity: Daily observations  

Both datasets are ingested and stored in Amazon S3 without modification in the raw zone.

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

## 6. Data Transformation & Feature Engineering

After merging, multiple transformations are applied:
- Timestamp parsing and standardization  
- Trip duration calculation  
- Rush hour identification  
- Day, month, and year extraction  
- Seasonal classification  
- Weather categorization (rain, snow, fog, thunder)  
- Wind speed and precipitation categorization  
- Round trip detection  
- Outlier handling for trip distance and duration  

These transformations enrich the dataset and make it analytics-ready.

---

## 7. Data Partitioning Strategy

- Data is stored in Parquet format  
- Partitioned by year and month  
- Enables efficient Athena partition pruning  
- Reduces query cost and improves performance  

---

## 8. Analytics & Visualization Layer

Power BI dashboards provide:
- Peak riding hours analysis  
- Station-level demand trends  
- User segmentation (member vs casual)  
- Weather impact on ridership  
- Geographic ride patterns using maps  

---

## 9. CI/CD & Project Management

- GitHub used for version control and collaboration  
- GitHub Actions automate ETL pipeline updates  
- Jira used for sprint planning, task tracking, and timelines  

---

## 10. Outcome & Business Value

- Scalable and cost-efficient analytics platform  
- Faster insights into demand patterns  
- Improved decision-making for bike allocation and planning  
- Production-grade cloud data engineering implementation  

---

## 11. Future Enhancements

- Demand forecasting using machine learning  
- Real-time streaming ingestion  
- Station-level recommendation engine  
- Automated anomaly detection  

---

This documentation serves as the foundation for the GitHub README and future project extensions.
