CREATE DATABASE saas_analytics;
USE saas_analytics;


-- Check if we have all 1,000 customers
SELECT COUNT(*) FROM customers;

-- Check the first few rows of revenue
SELECT * FROM revenue_events LIMIT 5;

-- Check the support ticket volume
SELECT category, COUNT(*) 
FROM support_tickets 
GROUP BY category;



-- Calculating Churn Rate by Billing Cycle 
SELECT
    billing_cycle,
    COUNT(*) AS total_customers,
    SUM(is_churned) AS churned_count,
    ROUND(SUM(is_churned) / COUNT(*) * 100, 2) AS churn_rate_percentage
FROM customers
GROUP BY billing_cycle;

-- Categorising Revenue
SELECT 
    event_month,
    event_type,
    SUM(mrr) AS total_mrr
FROM revenue_events
GROUP BY 1, 2
ORDER BY 1, total_mrr DESC;


-- Retention Cohort Analysis
-- Step 1: Get each customer's cohort month
WITH cohort_items AS (
    SELECT
        customer_id,
        DATE_FORMAT(signup_date, '%Y-%m') AS cohort_month
    FROM customers 
),

-- Step 2: Track their activity in subsequent months
user_activities AS (
    SELECT
        re.customer_id,
        ci.cohort_month,
        TIMESTAMPDIFF(
            MONTH,
            STR_TO_DATE(CONCAT(ci.cohort_month, '-01'), '%Y-%m-%d'),
            STR_TO_DATE(CONCAT(re.event_month,  '-01'), '%Y-%m-%d')
        ) AS month_number
    FROM revenue_events re
    JOIN cohort_items ci ON re.customer_id = ci.customer_id
)

-- Step 3: Pivot for the heatmap
SELECT
    cohort_month,
    month_number,
    COUNT(DISTINCT customer_id) AS active_users
FROM user_activities
GROUP BY 1, 2
ORDER BY 1, 2;


-- Support Tickets & Churn Correlation
SELECT 
    c.is_churned,
    AVG(c.usage_score) as avg_usage,
    ROUND(COUNT(st.ticket_id) / CAST(COUNT(DISTINCT c.customer_id) AS DECIMAL(10,2)),2) AS tickets_per_customer,
    ROUND(AVG(st.days_to_resolve),2) AS avg_resolution_time
FROM customers c
LEFT JOIN support_tickets st ON c.customer_id = st.customer_id
GROUP BY 1;



-- Identifying "At-Risk" Customers
SELECT 
    customer_id,
    plan_name,
    usage_score,
    billing_cycle
FROM customers
WHERE is_churned = 'Active' 
  AND usage_score < 40 -- Low engagement
  AND billing_cycle = 'Annual' -- Your high-risk segment
ORDER BY usage_score ASC
LIMIT 50;

SELECT is_churned,COUNT(is_churned)
FROM customers
GROUP BY is_churned;

SELECT event_month, SUM(mrr) as Total_MRR
FROM revenue_events
GROUP BY event_month
ORDER BY event_month;

SELECT billing_cycle, is_churned, COUNT(*) as User_Count
FROM customers
GROUP BY billing_cycle, is_churned;



