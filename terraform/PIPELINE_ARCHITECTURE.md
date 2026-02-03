# CitiBike Demand Optimization - End-to-End Pipeline Architecture

## Overview
This Terraform configuration sets up a fully automated, event-driven data pipeline for CitiBike demand optimization with the following flow:

```
S3 Upload (Raw CSV) 
    ↓ (EventBridge Trigger)
Glue Workflow Started
    ↓
Raw Crawler (Bronze Layer)
    ↓
Job 1: Bronze → Silver (Data Cleaning & Transformation)
    ↓
Silver Crawler (Update Glue Catalog)
    ↓
Job 2: Silver → Gold (Analytics Layer)
    ↓
Gold Crawler (Update Glue Catalog for Athena)
    ↓
Athena Ready for Queries
```

## Components

### 1. S3 Data Lake Structure
- **data/raw/citibike/** - Raw CSV files (Bronze layer)
- **data/silver/citibike/** - Cleaned & transformed Parquet (partitioned by year/month/day)
- **data/gold/citibike/** - Analytics-ready Parquet (optimized for Athena)
- **glue_scripts/** - Python ETL scripts
- **temp/** - Temporary working files (auto-deleted after 7 days)
- **logs/** - Spark UI logs (auto-deleted after 30 days)
- **athena-results/** - Athena query results (auto-deleted after 7 days)

### 2. EventBridge Integration (S3 → Glue)

**EventBridge Rule**: `citibike-{environment}-s3-upload-trigger`
- **Trigger**: Object created in `data/raw/citibike/` with `.csv` extension
- **Target**: Starts Glue Workflow
- **Role**: `eventbridge_glue_role` (has permission to start workflow)

**Event Pattern**:
```json
{
  "source": ["aws.s3"],
  "detail-type": ["Object Created"],
  "detail": {
    "bucket": {"name": ["<bucket-name>"]},
    "object": {
      "key": [
        {"prefix": "data/raw/citibike/"},
        {"suffix": ".csv"}
      ]
    }
  }
}
```

### 3. Glue Workflow Orchestration

**Workflow**: `citibike-{environment}-etl-workflow`

#### Trigger Sequence:

1. **Start Raw Crawler** (ON_DEMAND)
   - Triggered when workflow starts
   - Crawls `data/raw/citibike/` folder
   - Creates/updates metadata in Glue Catalog for raw tables

2. **Raw Crawler SUCCESS → Job 1** (CONDITIONAL)
   - Job 1: Bronze to Silver transformation
   - Reads raw CSV from `data/raw/citibike/`
   - Writes partitioned Parquet to `data/silver/citibike/`
   - Partition keys: year, month, day

3. **Job 1 SUCCESS → Silver Crawler** (CONDITIONAL)
   - Crawls `data/silver/citibike/` folder
   - Updates Glue Catalog with silver layer metadata
   - Detects partition structure (year/month/day)

4. **Silver Crawler SUCCESS → Job 2** (CONDITIONAL)
   - Job 2: Silver to Gold transformation
   - Reads partitioned Parquet from `data/silver/citibike/`
   - Applies aggregations and optimizations
   - Writes partitioned Parquet to `data/gold/citibike/`

5. **Job 2 SUCCESS → Gold Crawler** (CONDITIONAL)
   - Crawls `data/gold/citibike/` folder
   - Updates Glue Catalog with gold layer metadata
   - Makes data immediately queryable via Athena

### 4. Glue Jobs

#### Job 1: Bronze to Silver (`job1_bronze_to_silver.py`)
```python
INPUT:  s3://<bucket>/data/raw/citibike/*.csv
OUTPUT: s3://<bucket>/data/silver/citibike/year=YYYY/month=MM/day=DD/*.parquet

Configuration:
- Python 3 (Spark)
- 2 G.1X workers
- Glue Version: 4.0
- Job bookmarks: ENABLED (incremental processing)
- Output format: Parquet
- Partition keys: year, month, day
```

#### Job 2: Silver to Gold (`job2_silver_to_gold.py`)
```python
INPUT:  s3://<bucket>/data/silver/citibike/year=*/month=*/day=*/*.parquet
OUTPUT: s3://<bucket>/data/gold/citibike/year=YYYY/month=MM/day=DD/*.parquet

Configuration:
- Python 3 (Spark)
- 2 G.1X workers
- Glue Version: 4.0
- Job bookmarks: ENABLED
- Output format: Parquet
- Partition keys: year, month, day
```

### 5. Glue Crawlers

#### Raw Data Crawler
- **Database**: `citibike_<environment>_db`
- **Target**: `s3://<bucket>/data/raw/citibike/`
- **Schedule**: NONE (Event-driven only via workflow)
- **Table name**: `raw_citibike` (auto-generated)

#### Silver Crawler
- **Database**: `citibike_<environment>_db`
- **Target**: `s3://<bucket>/data/silver/citibike/`
- **Partitions**: Detects year/month/day partitions
- **Table name**: `silver_citibike` (auto-generated)

#### Gold Crawler
- **Database**: `citibike_<environment>_db`
- **Target**: `s3://<bucket>/data/gold/citibike/`
- **Partitions**: Detects year/month/day partitions
- **Table name**: `gold_citibike` (auto-generated)

### 6. IAM Roles & Permissions

#### EventBridge Role (`eventbridge_glue_role`)
- Assumes: `events.amazonaws.com` service
- Permissions: `glue:StartWorkflowRun`, `glue:notifyEvent`
- Resource: Glue workflow ARN

#### Glue Service Role (`glue_role`)
- Assumes: `glue.amazonaws.com` service
- AWS Managed: `AWSGlueServiceRole`
- Custom: S3 access to entire data lake bucket
- Permissions: GetObject, PutObject, DeleteObject, ListBucket

#### Lambda Role (`lambda_role`)
- Assumes: `lambda.amazonaws.com` service
- AWS Managed: `AWSLambdaBasicExecutionRole`
- Custom: S3 and Glue read permissions

#### CI/CD User (`cicd_user`)
- S3: Upload/download Glue scripts and Lambda code
- Glue: Start/update jobs and workflows
- Lambda: Update function code
- IAM: PassRole to Glue and Lambda services

## Data Flow Example

### Step 1: File Upload
```bash
# User uploads CSV to S3
aws s3 cp sales_data_2025_01.csv s3://citibike-datalake/data/raw/citibike/
```

### Step 2: EventBridge Detection
```
Time: T+0s
- S3 sends "Object Created" event to EventBridge
- EventBridge rule matches: prefix=data/raw/citibike/, suffix=.csv
- EventBridge invokes Glue Workflow
```

### Step 3: Workflow Execution
```
Time: T+10s  → Raw Crawler starts, crawls raw CSV
Time: T+20s  → Raw Crawler succeeds, discovers table schema
Time: T+25s  → Job 1 starts, reads raw CSV, writes silver Parquet
Time: T+120s → Job 1 succeeds, data in silver layer
Time: T+125s → Silver Crawler starts, crawls partitioned Parquet
Time: T+135s → Silver Crawler succeeds, updates Glue Catalog
Time: T+140s → Job 2 starts, reads silver layer, aggregates
Time: T+180s → Job 2 succeeds, gold data ready
Time: T+185s → Gold Crawler starts
Time: T+195s → Gold Crawler succeeds, Glue Catalog updated
```

### Step 4: Athena Access
```python
# Immediately after gold crawler succeeds, data is queryable
import boto3
athena = boto3.client('athena')

query = """
SELECT 
    year, month, day,
    COUNT(*) as trip_count,
    AVG(duration) as avg_duration
FROM citibike_test_db.gold_citibike
WHERE year=2025 AND month=01
GROUP BY year, month, day
"""

response = athena.start_query_execution(
    QueryString=query,
    QueryExecutionContext={'Database': 'citibike_test_db'},
    ResultConfiguration={'OutputLocation': 's3://citibike-datalake/athena-results/'}
)
```

## Configuration Variables

See `terraform.tfvars`:

```hcl
aws_region         = "eu-north-1"      # AWS region
environment        = "test"            # Environment (test/prod)
project_name       = "citibike"        # Project prefix
s3_bucket_name     = "citibike-datalake-xxx"  # Unique S3 bucket
enable_versioning  = true              # S3 versioning
glue_python_version = "3"              # Python version
glue_worker_type   = "G.1X"            # Worker type (G.1X or G.2X)
glue_number_of_workers = 2             # Number of workers
citibike_year      = "2025"            # Processing year
```

## Monitoring & Debugging

### CloudWatch Logs
- Glue job logs: `/aws-glue/jobs/citibike-{environment}-job1-*`
- Glue job logs: `/aws-glue/jobs/citibike-{environment}-job2-*`
- Crawler logs: `/aws-glue/crawlers/citibike-{environment}-*-crawler`

### EventBridge Rule Testing
```bash
# Test EventBridge rule
aws events test-event-pattern \
  --event-pattern '{"source":["aws.s3"],"detail-type":["Object Created"],...}' \
  --event '{"source":"aws.s3","detail-type":"Object Created","detail":{"bucket":{"name":"citibike-datalake"},"object":{"key":"data/raw/citibike/test.csv"}}}'
```

### Glue Workflow Status
```bash
# Check workflow status
aws glue get-workflow-runs --name citibike-test-etl-workflow

# Check specific run
aws glue get-workflow-run --name citibike-test-etl-workflow --run-id <run-id>
```

### Glue Catalog Query
```bash
# List databases
aws glue get-databases

# List tables in database
aws glue get-tables --database-name citibike_test_db

# Get table details
aws glue get-table --database-name citibike_test_db --name gold_citibike
```

## Deployment Instructions

### 1. Initialize Terraform
```bash
cd terraform
terraform init
```

### 2. Plan Changes
```bash
terraform plan -out=tfplan
```

### 3. Apply Configuration
```bash
terraform apply tfplan
```

### 4. Verify Deployment
```bash
# Get outputs
terraform output

# Expected outputs:
# - s3_bucket_name
# - glue_database_name
# - workflow_name
# - eventbridge_role_arn
# - raw_data_path, silver_data_path, gold_data_path
```

### 5. Deploy Glue Scripts
```bash
# Upload Job 1 script
aws s3 cp glue_jobs/Merge_Cleaning_And_Transformation\(Silver\).py \
  s3://<bucket>/glue_scripts/latest/job1_bronze_to_silver.py

# Upload Job 2 script
aws s3 cp glue_jobs/gold_transformation.py \
  s3://<bucket>/glue_scripts/latest/job2_silver_to_gold.py
```

## Testing the Pipeline

### 1. Upload Sample Data
```bash
# Create sample CSV
cat > sample.csv << EOF
ride_id,bike_id,start_time,end_time,start_station,end_station,duration,user_type
1,101,2025-01-15 08:00:00,2025-01-15 08:15:00,Station A,Station B,900,Subscriber
2,102,2025-01-15 09:00:00,2025-01-15 09:25:00,Station B,Station C,1500,Casual
EOF

# Upload to S3
aws s3 cp sample.csv s3://citibike-datalake/data/raw/citibike/2025_01_15_sample.csv
```

### 2. Monitor Workflow
```bash
# Get workflow runs
aws glue get-workflow-runs --name citibike-test-etl-workflow

# Monitor specific run
watch -n 5 'aws glue get-workflow-run --name citibike-test-etl-workflow --run-id <run-id>'
```

### 3. Query Results via Athena
```bash
aws athena start-query-execution \
  --query-string "SELECT * FROM citibike_test_db.gold_citibike LIMIT 10" \
  --query-execution-context Database=citibike_test_db \
  --result-configuration OutputLocation=s3://citibike-datalake/athena-results/
```

## Troubleshooting

### Issue: EventBridge not triggering workflow
- **Check**: S3 bucket has EventBridge notification enabled
- **Check**: Object matches event pattern (path and extension)
- **Check**: EventBridge rule is enabled
- **Check**: IAM role has permission to start workflow

### Issue: Glue job fails
- **Check**: S3 paths are correct
- **Check**: Glue job script exists at specified location
- **Check**: Job has sufficient IAM permissions
- **Check**: CloudWatch logs for error details

### Issue: Crawler not updating Glue Catalog
- **Check**: Crawler has permission to read S3
- **Check**: Data format matches expected schema
- **Check**: Partition structure is correct (year/month/day)

### Issue: Athena cannot query gold data
- **Check**: Gold crawler has completed successfully
- **Check**: Glue Catalog database and table exist
- **Check**: Parquet files are valid

## Optimization Notes

1. **Job Bookmarks**: Enabled on both jobs for incremental processing
2. **Partitioning**: year/month/day partitions enable predicate pushdown
3. **Parquet Format**: Columnar format optimized for analytics
4. **Crawler Partitions**: Auto-detection of partition structure
5. **Lifecycle Policies**: Automatic cleanup of temp, logs, and query results
6. **Worker Type**: G.1X workers provide good cost/performance balance

## Cost Considerations

- **Glue**: Pay per job run duration (2 G.1X workers per job)
- **Crawlers**: Pay per crawler runtime
- **S3**: Pay for storage and requests
- **Athena**: Pay per scanned bytes (Parquet compression reduces cost)
- **EventBridge**: Free tier covers most workloads

## Future Enhancements

1. Add data quality checks between layers
2. Implement automatic data validation
3. Add cost monitoring and alerts
4. Implement data retention policies
5. Add machine learning predictions
6. Implement real-time streaming pipeline
