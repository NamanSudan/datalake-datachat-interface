# Metrics Table: Query Documentation

This document provides comprehensive documentation for common queries on the `observability.Metrics` table based on the patterns found in the training data.

## Purpose of the Metrics Table

The Metrics table serves as a central repository for tracking performance metrics related to applications and servers within our Clickhouse database. It stores detailed metric data about CPU load, memory usage, response times, and other key performance indicators, allowing for effective monitoring and analysis of system performance.

## Schema Overview

The Metrics table is stored in the observability database and contains fields for identifying applications (`AppId`, `CI`, `AppName`), categorizing metrics (`MetricPath`), and capturing metric values (`CurrentValue`). The table also includes temporal data to track when metrics were collected (`Timestamp`, `MetricStartTime`).

## Common Query Patterns

### 1. Monitoring Overview Query

This query pattern is used to get a high-level overview of what applications and servers are being monitored in the system.

**Use Case**: Understanding the scope of monitoring coverage and identifying the different data sources.

**Query Example**:
```sql
SELECT DISTINCT Sources, AppName, Controller 
FROM observability.Metrics
```

**Key Components**:
- `DISTINCT` ensures we get unique combinations
- Selected fields provide a three-dimensional view of the monitoring landscape:
  - `Sources`: Where the metric data originated (e.g., "AppDynamics", "Dynatrace")
  - `AppName`: The application being monitored
  - `Controller`: The environment where the application is running

**Sample Question**: "What applications / servers are being monitored?"

### 2. CPU Load for Specific Application

This query pattern helps in monitoring CPU utilization for a specific application by name.

**Use Case**: Tracking CPU performance for a particular application to identify potential resource constraints.

**Query Example**:
```sql
SELECT AppName, MetricPath, CurrentValue, Timestamp 
FROM observability.Metrics 
WHERE AppName='AGQA_CVS_PBM_Clarity' 
AND MetricPath like '%CPU%' 
AND MetricPath like '%Busy%';
```

**Key Components**:
- Application filtering: Targets a specific application by name
- Metric type filtering: Uses multiple LIKE conditions on MetricPath to find CPU metrics
- Selected fields include:
  - The hierarchical metric path for context
  - The actual metric value
  - The timestamp for temporal analysis

**Sample Question**: "What is the cpu load for AGQA_CVS_PBM_Clarity?"

### 3. CPU Load for Specific Server with Time Window

This query pattern monitors CPU utilization for a specific server over a defined time period.

**Use Case**: Analyzing recent CPU performance trends for a particular server.

**Query Example**:
```sql
SELECT CurrentValue as cpu_laod, Timestamp, MetricStartTime 
FROM observability.Metrics 
WHERE MetricPath like '%CPU|\%Busy' 
AND MetricPath like '%azbwvqa1cmdap04.ahm.corp%' 
AND Timestamp >= now() - INTERVAL 24 HOUR;
```

**Key Components**:
- Server identification: Uses the server name in MetricPath
- Time window: Limits to the last 24 hours
- Field aliasing: Renames CurrentValue for clarity
- Includes MetricStartTime to understand the metric calculation period

**Related Context**: "When using MetricPath, we should be using like '%keyword' to search for type of metric. For example to find cpu load, we check MetricPath like %CPU and %Busy."

### 4. Memory Load for Specific Server with Time Window

This query pattern tracks memory utilization for a specific server over a defined time period.

**Use Case**: Analyzing recent memory consumption trends for a particular server.

**Query Example**:
```sql
SELECT CurrentValue as memory_load_percentage, Timestamp 
FROM observability.Metrics 
WHERE MetricPath like '%Memory|Used%' 
AND MetricPath like '%azbwvqa1cmdap04.ahm.corp%' 
AND Timestamp >= now() - INTERVAL 24 HOUR;
```

**Key Components**:
- Memory metric identification: Uses 'Memory|Used' in MetricPath
- Server filtering: Targets a specific server
- Time windowing: Focuses on the last 24 hours
- Value aliasing: Renames CurrentValue for clarity

**Related Context**: "When a user asks for memory load, we are looking Memory|Used."

### 5. Overall Application Health Query

This query pattern examines the overall health metrics for a specific application.

**Use Case**: Getting a high-level view of an application's performance health.

**Query Example**:
```sql
SELECT MetricPath, CurrentValue 
FROM observability.Metrics 
WHERE AppName = 'ahm_activeadvice_web_prod' 
AND MetricPath like 'Overall Application Performance' 
ORDER BY Timestamp DESC 
LIMIT 20;
```

**Key Components**:
- Application filtering: Targets a specific application
- Health metric focus: Looks specifically at 'Overall Application Performance'
- Recency prioritization: Orders by timestamp descending
- Result limiting: Caps at 20 records for manageability

**Related Context**: "Overall application health can be searched for in the Metrics table in column MetricPath."

### 6. Database Health Monitoring Query

This complex query pattern evaluates the health of monitored databases across multiple dimensions.

**Use Case**: Comprehensive health assessment of database systems to identify issues requiring attention.

**Query Example**:
```sql
WITH distinct_databases AS (
    SELECT DISTINCT extract(MetricPath, 'Databases\|([^|]+)\|') AS DatabaseName
    FROM observability.metrics
    WHERE AppName = 'Database Monitoring'
    LIMIT 10
),
db_availability AS (
    SELECT
        MetricPath,
        CurrentValue,
        Timestamp,
        'DB Availability' AS MetricCategory,
        extract(MetricPath, 'Databases\|([^|]+)\|') AS DatabaseName,
        if(CurrentValue = 0, 'DB Availability is Down', NULL) AS HealthReason
    FROM
        observability.metrics
    WHERE
        MetricPath LIKE '%DB Availability%'
        AND extract(MetricPath, 'Databases\|([^|]+)\|') GLOBAL IN (SELECT DatabaseName FROM distinct_databases)
        AND AppName = 'Database Monitoring'
),
cpu_busy AS (
    SELECT
        MetricPath,
        CurrentValue,
        Timestamp,
        'CPU Busy' AS MetricCategory,
        extract(MetricPath, 'Databases\|([^|]+)\|') AS DatabaseName,
        if(CurrentValue >= 95, 'CPU is Busier than 95%', NULL) AS HealthReason
    FROM 
        observability.metrics
    WHERE
        MetricPath LIKE '%|CPU|%Busy%'
        AND extract(MetricPath, 'Databases\|([^|]+)\|') GLOBAL IN (SELECT DatabaseName FROM distinct_databases)
        AND AppName = 'Database Monitoring'
),
process_blocked AS (
    SELECT
        MetricPath,
        CurrentValue,
        Timestamp,
        'Process Blocked' AS MetricCategory,
        extract(MetricPath, 'Databases\|([^|]+)\|') AS DatabaseName,
        if(CurrentValue != 0, 'Process is Blocked', NULL) AS HealthReason
    FROM 
        observability.metrics
    WHERE
        MetricPath LIKE '%Process Blocked%'
        AND extract(MetricPath, 'Databases\|([^|]+)\|') GLOBAL IN (SELECT DatabaseName FROM distinct_databases)
        AND AppName = 'Database Monitoring'
),
number_of_connections AS (
    SELECT
        MetricPath,
        CurrentValue,
        Timestamp,
        'Number of Connections' AS MetricCategory,
        extract(MetricPath, 'Databases\|([^|]+)\|') AS DatabaseName,
        if((CurrentValue = 0) OR (CurrentValue > 2), 'Number of Connections is not optimal', NULL) AS HealthReason
    FROM 
        observability.metrics
    WHERE
        MetricPath LIKE '%Number of Connections%'
        AND extract(MetricPath, 'Databases\|([^|]+)\|') GLOBAL IN (SELECT DatabaseName FROM distinct_databases)
        AND AppName = 'Database Monitoring'
),
time_spent_in_executions AS (
    SELECT
        MetricPath,
        CurrentValue,
        Timestamp,
        'Time Spent in Executions' AS MetricCategory,
        extract(MetricPath, 'Databases\|([^|]+)\|') AS DatabaseName,
        if(CurrentValue >= 300, 'Time Spent in Executions is higher than 5 mins', NULL) AS HealthReason
    FROM 
        observability.metrics
    WHERE
        MetricPath LIKE '%Time Spent in Executions%'
        AND extract(MetricPath, 'Databases\|([^|]+)\|') GLOBAL IN (SELECT DatabaseName FROM distinct_databases)
        AND AppName = 'Database Monitoring'
),
combined_metrics AS (
    SELECT * FROM db_availability
    UNION ALL
    SELECT * FROM cpu_busy
    UNION ALL
    SELECT * FROM process_blocked
    UNION ALL
    SELECT * FROM number_of_connections
    UNION ALL
    SELECT * FROM time_spent_in_executions
),
unhealthy_metrics AS (
    SELECT
        DatabaseName,
        MetricPath,
        Timestamp,
        HealthReason
    FROM
        combined_metrics
    WHERE
        HealthReason IS NOT NULL
),
health_assessment AS (
    SELECT
        DatabaseName,
        groupArrayDistinct(HealthReason) AS ReasonArray,
        max(Timestamp) AS LatestTimestamp,
        groupArrayDistinct(MetricPath) AS MetricPaths
    FROM
        unhealthy_metrics
    GROUP BY
        DatabaseName
)
SELECT
    DatabaseName,
    arrayStringConcat(ReasonArray, ', ') AS Reasons,
    LatestTimestamp AS Timestamp,
    arrayStringConcat(MetricPaths, ', ') AS MetricPath
FROM
    health_assessment
ORDER BY
    DatabaseName;
```

**Key Components**:
- Hierarchical CTE structure assessing five key health dimensions:
  1. Database availability
  2. CPU utilization
  3. Process blocking
  4. Connection count
  5. Query execution time
- MetricPath extraction to identify database names
- Conditional health reason assignment based on threshold values
- Aggregation of issues per database
- Final output showing databases with issues, their reasons, and latest timestamps

**Sample Questions**:
- "How is the database health?"
- "Show me unhealthy databases"
- "Are there any database issues?"
- "Check database performance"

### 7. Find Databases with High CPU Utilization

This query pattern identifies databases that are experiencing high CPU utilization, which could indicate performance issues.

**Use Case**: Monitoring database performance to identify systems that may be overloaded or experiencing resource constraints.

**Query Example**:
```sql
SELECT
    DISTINCT extract(MetricPath, 'Databases\|([^|]+)\|') AS DatabaseName,
    MetricPath,
    CurrentValue AS CpuUtilization,
    Timestamp
FROM observability.metrics
WHERE MetricPath LIKE '%|CPU|%Busy%'
AND AppName = 'Database Monitoring'
AND CurrentValue >= 95  -- Threshold matches db_health.sql
ORDER BY CpuUtilization DESC
LIMIT 50
```

**Key Components**:
- Database name extraction: Uses extract function with regex pattern to pull database name from MetricPath
- Metric filtering: Focuses on CPU busy metrics
- Threshold: Identifies databases with CPU utilization at or above 95%
- Result ordering: Shows highest utilization first

**Sample Question**: "Which databases have high CPU utilization?"

### 8. Find Databases with Long Query Execution Times

This query pattern identifies databases that are experiencing long query execution times, which may indicate performance issues.

**Use Case**: Identifying databases with potentially inefficient queries or resource bottlenecks.

**Query Example**:
```sql
SELECT
    DISTINCT extract(MetricPath, 'Databases\|([^|]+)\|') AS DatabaseName,
    MetricPath,
    CurrentValue AS ExecutionTimeMs,
    Timestamp
FROM observability.metrics
WHERE MetricPath LIKE '%Time Spent in Executions%'
AND AppName = 'Database Monitoring'
AND CurrentValue >= 300000  -- 5 minutes in milliseconds, matches db_health.sql threshold
ORDER BY ExecutionTimeMs DESC
LIMIT 50
```

**Key Components**:
- Database name extraction: Uses extract function with regex pattern
- Time metric focus: Targets execution time metrics
- Millisecond threshold: Identifies databases with execution times at or above 5 minutes (300,000 ms)
- Result ordering: Shows longest execution times first

**Sample Question**: "Which databases have slow query execution times?"

### 9. Find Databases with Availability Issues

This query pattern identifies databases that are experiencing availability issues, which could indicate they are down or unreachable.

**Use Case**: Monitoring database availability to quickly identify systems that may be offline or experiencing connectivity issues.

**Query Example**:
```sql
SELECT
    DISTINCT extract(MetricPath, 'Databases\|([^|]+)\|') AS DatabaseName,
    MetricPath,
    CurrentValue AS AvailabilityStatus,
    Timestamp
FROM observability.metrics
WHERE MetricPath LIKE '%DB Availability%'
AND AppName = 'Database Monitoring'
AND CurrentValue = 0  -- Matches db_health.sql threshold (0 = down)
ORDER BY Timestamp DESC
LIMIT 50
```

**Key Components**:
- Database name extraction: Uses extract function with regex pattern
- Availability metric focus: Targets database availability status
- Binary threshold: Identifies databases with availability status of 0 (down)
- Recency ordering: Shows most recent issues first

**Sample Question**: "Which databases are currently down or unavailable?"

### 10. Find Databases with Blocked Processes

This query pattern identifies databases that have blocked processes, which could indicate deadlocks or resource contentions.

**Use Case**: Identifying databases experiencing transaction or query blockage that may impact performance and cause application delays.

**Query Example**:
```sql
SELECT
    DISTINCT extract(MetricPath, 'Databases\|([^|]+)\|') AS DatabaseName,
    MetricPath,
    CurrentValue AS BlockedProcessCount,
    Timestamp
FROM observability.metrics
WHERE MetricPath LIKE '%Process Blocked%'
AND AppName = 'Database Monitoring'
AND CurrentValue > 0  -- Matches db_health.sql threshold
ORDER BY BlockedProcessCount DESC
LIMIT 50
```

**Key Components**:
- Database name extraction: Uses extract function with regex pattern
- Process blocking focus: Targets blocked process metrics
- Threshold: Identifies any database with blocked processes (count > 0)
- Result ordering: Shows databases with most blocked processes first

**Sample Question**: "Which databases have blocked processes?"

### 11. Find Databases with Connection Issues

This query pattern identifies databases that have connection count issues, either too few (0) or too many.

**Use Case**: Monitoring database connection patterns to identify potential connectivity or resource allocation problems.

**Query Example**:
```sql
SELECT
    DISTINCT extract(MetricPath, 'Databases\|([^|]+)\|') AS DatabaseName,
    MetricPath,
    CurrentValue AS ConnectionCount,
    Timestamp
FROM observability.metrics
WHERE MetricPath LIKE '%Number of Connections%'
AND AppName = 'Database Monitoring'
AND (CurrentValue = 0 OR CurrentValue > 2)  -- Matches db_health.sql threshold
ORDER BY Timestamp DESC
LIMIT 50
```

**Key Components**:
- Database name extraction: Uses extract function with regex pattern
- Connection focus: Targets connection count metrics
- Dual threshold: Identifies databases with no connections (= 0) or too many connections (> 2)
- Recency ordering: Shows most recent issues first

**Sample Question**: "Which databases have connection issues?"

## Best Practices for Querying the Metrics Table

1. **Always use MetricPath LIKE patterns effectively**: 
   - Use multiple LIKE conditions for more precise filtering
   - Consider the hierarchical structure with | delimiters

2. **Include time filtering**: 
   - The Metrics table can be very large, so always include a time filter using the `Timestamp` field
   - Common patterns use `now() - INTERVAL X HOUR/DAY`

3. **Consider both CI and AppName for application identification**:
   - Use `WHERE (CI='application' OR AppName='application')` to ensure complete results

4. **Use aliasing for clarity**:
   - Rename values with `as` to make them more meaningful (e.g., `CurrentValue as cpu_load`)

5. **Limit results when appropriate**:
   - Use `LIMIT`, `ORDER BY Timestamp DESC`, or aggregation to manage result set size 

6. **Extract database names properly**:
   - Use `DISTINCT extract(MetricPath, 'Databases\|([^|]+)\|')` to reliably extract database names from MetricPath 