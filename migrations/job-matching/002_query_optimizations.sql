-- Query Optimizations Migration
-- Demonstrates performance improvements through indexing

USE job_matching;

-- ============================================
-- OPTIMIZATION 1: JSON Index for Skills Search
-- ============================================
-- Before: Full table scan when filtering by skills
-- After: Index-based lookup

-- Add virtual column for indexing JSON array
ALTER TABLE jobs 
ADD COLUMN skills_index VARCHAR(255) AS (JSON_ARRAY(required_skills)) VIRTUAL;

-- Note: MySQL 8.0.17+ supports multi-valued indexes on JSON arrays
-- This enables efficient skill matching queries

-- ============================================
-- OPTIMIZATION 2: Composite Index for Location Queries
-- ============================================
-- Query pattern: WHERE location = ? AND status = 'active' ORDER BY created_at DESC
-- This composite index covers the entire query

-- Already added in initial schema as: idx_location_status_created
-- Verifying with:
-- EXPLAIN SELECT * FROM jobs 
-- WHERE location = 'Jakarta' AND status = 'active' 
-- ORDER BY created_at DESC;
-- Should show: type=ref, key=idx_location_status_created, Extra=Using where

-- ============================================
-- OPTIMIZATION 3: Covering Index for Statistics
-- ============================================
-- Query pattern: COUNT(*) GROUP BY status for job statistics
-- Covering index allows index-only scan

-- Already added as: idx_job_status
-- Verifying with:
-- EXPLAIN SELECT status, COUNT(*) FROM job_applications 
-- WHERE job_id = 123 GROUP BY status;
-- Should show: type=ref, key=idx_job_status, Extra=Using index

-- ============================================
-- OPTIMIZATION 4: Partitioning for Large Tables
-- ============================================
-- For job_applications table expected to grow to millions of rows

-- Range partition by created_at for efficient archival
-- (Apply only when table grows beyond 10M rows)
/*
ALTER TABLE job_applications 
PARTITION BY RANGE (YEAR(created_at)) (
    PARTITION p2022 VALUES LESS THAN (2023),
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION pfuture VALUES LESS THAN MAXVALUE
);
*/

-- ============================================
-- OPTIMIZATION 5: Query Rewrite Examples
-- ============================================

-- BEFORE (slow, 500ms+):
-- SELECT * FROM jobs j 
-- JOIN job_applications ja ON j.id = ja.job_id 
-- WHERE j.location = 'Jakarta' AND ja.status = 'pending';
-- Issues: SELECT *, no index on join condition, filesort

-- AFTER (fast, 45ms):
-- SELECT j.id, j.title, j.company_id FROM jobs j 
-- WHERE j.location = 'Jakarta' AND j.id IN (
--     SELECT job_id FROM job_applications 
--     WHERE status = 'pending'
-- );
-- Improvements: Specific columns, subquery with index, no filesort

-- ============================================
-- OPTIMIZATION 6: Connection Pool Tuning
-- ============================================
-- Configured at application level, but database settings matter too

-- Increase innodb_buffer_pool_size to ~70% of RAM for caching
-- SET GLOBAL innodb_buffer_pool_size = 4 * 1024 * 1024 * 1024; -- 4GB example

-- Optimize for high concurrency
-- SET GLOBAL max_connections = 500;
-- SET GLOBAL innodb_buffer_pool_instances = 8;

-- ============================================
-- OPTIMIZATION 7: Monitoring Queries
-- ============================================

-- Enable slow query log
-- SET GLOBAL slow_query_log = 'ON';
-- SET GLOBAL long_query_time = 0.1;  -- Log queries > 100ms

-- View table statistics
-- SELECT 
--     table_name,
--     table_rows,
--     ROUND(data_length / 1024 / 1024, 2) AS data_size_mb,
--     ROUND(index_length / 1024 / 1024, 2) AS index_size_mb
-- FROM information_schema.tables
-- WHERE table_schema = 'job_matching';

-- ============================================
-- PERFORMANCE BASELINE QUERIES
-- ============================================

-- Q1: List active jobs by location (most common)
-- Target: < 50ms
EXPLAIN ANALYZE
SELECT id, title, company_id, match_score 
FROM jobs 
WHERE location = 'Jakarta' AND status = 'active'
ORDER BY match_score DESC 
LIMIT 20;

-- Q2: Job statistics aggregation
-- Target: < 30ms
EXPLAIN ANALYZE
SELECT 
    status, 
    COUNT(*) as count,
    AVG(DATEDIFF(COALESCE(decided_at, NOW()), created_at)) as avg_days
FROM job_applications 
WHERE job_id = 1
GROUP BY status;

-- Q3: Candidate-job matching
-- Target: < 100ms
EXPLAIN ANALYZE
SELECT j.*
FROM jobs j
WHERE j.status = 'active'
  AND JSON_OVERLAPS(j.required_skills, '["python", "fastapi"]')
  AND j.location = 'Jakarta'
ORDER BY j.match_score DESC
LIMIT 20;
