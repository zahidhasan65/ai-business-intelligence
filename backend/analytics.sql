CREATE SCHEMA IF NOT EXISTS olist_bi;

-- ============================================================
-- 1. EXECUTIVE KPIs
-- ============================================================

CREATE OR REPLACE VIEW olist_bi.v_executive_kpis AS
SELECT
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT CASE
        WHEN o.order_status = 'delivered' THEN o.order_id
    END) AS delivered_orders,
    COUNT(DISTINCT c.customer_unique_id) AS total_customers,
    COUNT(DISTINCT p.product_id) AS total_products,
    COUNT(DISTINCT s.seller_id) AS total_sellers,
    COALESCE(SUM(oi.price), 0)::NUMERIC(14,2) AS total_revenue,
    CASE
        WHEN COUNT(DISTINCT o.order_id) > 0
        THEN (
            SUM(oi.price) /
            COUNT(DISTINCT o.order_id)
        )::NUMERIC(14,2)
        ELSE 0
    END AS average_order_value
FROM olist_bi.orders o
LEFT JOIN olist_bi.order_items oi
    ON o.order_id = oi.order_id
LEFT JOIN olist_bi.customers c
    ON o.customer_id = c.customer_id
LEFT JOIN olist_bi.products p
    ON oi.product_id = p.product_id
LEFT JOIN olist_bi.sellers s
    ON oi.seller_id = s.seller_id;


-- ============================================================
-- 2. MONTHLY SALES
-- ============================================================

CREATE OR REPLACE VIEW olist_bi.v_monthly_sales AS
WITH monthly AS (
    SELECT
        DATE_TRUNC(
            'month',
            o.order_purchase_timestamp
        )::DATE AS month,
        COUNT(DISTINCT o.order_id) AS orders,
        COALESCE(SUM(oi.price), 0)::NUMERIC(14,2) AS revenue
    FROM olist_bi.orders o
    JOIN olist_bi.order_items oi
        ON o.order_id = oi.order_id
    GROUP BY 1
),
with_previous AS (
    SELECT
        month,
        orders,
        revenue,
        LAG(revenue) OVER (
            ORDER BY month
        ) AS previous_revenue
    FROM monthly
)
SELECT
    month,
    orders,
    revenue,
    CASE
        WHEN previous_revenue IS NULL
             OR previous_revenue = 0
        THEN NULL
        ELSE (
            (revenue - previous_revenue)
            / previous_revenue * 100
        )::NUMERIC(10,2)
    END AS revenue_growth_pct
FROM with_previous
ORDER BY month;


-- ============================================================
-- 3. TOP PRODUCTS
-- ============================================================

CREATE OR REPLACE VIEW olist_bi.v_top_products AS
SELECT
    p.product_id,
    COALESCE(
        ct.product_category_name_english,
        p.product_category_name,
        'unknown'
    ) AS category,
    COUNT(DISTINCT oi.order_id) AS orders,
    COUNT(*) AS units_sold,
    COALESCE(SUM(oi.price), 0)::NUMERIC(14,2) AS revenue,
    COALESCE(AVG(oi.price), 0)::NUMERIC(12,2) AS average_price
FROM olist_bi.products p
JOIN olist_bi.order_items oi
    ON p.product_id = oi.product_id
LEFT JOIN olist_bi.category_translation ct
    ON p.product_category_name =
       ct.product_category_name
GROUP BY
    p.product_id,
    ct.product_category_name_english,
    p.product_category_name
ORDER BY revenue DESC;


-- ============================================================
-- 4. CATEGORY PERFORMANCE
-- ============================================================

CREATE OR REPLACE VIEW olist_bi.v_category_performance AS
SELECT
    COALESCE(
        ct.product_category_name_english,
        p.product_category_name,
        'unknown'
    ) AS category,
    COUNT(DISTINCT oi.order_id) AS orders,
    COUNT(*) AS units_sold,
    COALESCE(SUM(oi.price), 0)::NUMERIC(14,2) AS revenue,
    COALESCE(AVG(oi.price), 0)::NUMERIC(12,2) AS average_price
FROM olist_bi.order_items oi
JOIN olist_bi.products p
    ON oi.product_id = p.product_id
LEFT JOIN olist_bi.category_translation ct
    ON p.product_category_name =
       ct.product_category_name
GROUP BY
    ct.product_category_name_english,
    p.product_category_name
ORDER BY revenue DESC;


-- ============================================================
-- 5. SELLER PERFORMANCE
-- ============================================================

CREATE OR REPLACE VIEW olist_bi.v_seller_performance AS
SELECT
    s.seller_id,
    s.seller_city,
    s.seller_state,
    COUNT(DISTINCT oi.order_id) AS orders,
    COUNT(*) AS units_sold,
    COALESCE(SUM(oi.price), 0)::NUMERIC(14,2) AS revenue,
    COALESCE(AVG(oi.price), 0)::NUMERIC(12,2) AS average_item_price
FROM olist_bi.sellers s
JOIN olist_bi.order_items oi
    ON s.seller_id = oi.seller_id
GROUP BY
    s.seller_id,
    s.seller_city,
    s.seller_state
ORDER BY revenue DESC;


-- ============================================================
-- 6. PAYMENT ANALYTICS
-- ============================================================

CREATE OR REPLACE VIEW olist_bi.v_payment_analytics AS
SELECT
    payment_type,
    COUNT(*) AS payment_count,
    COALESCE(SUM(payment_value), 0)::NUMERIC(14,2)
        AS total_payment_value,
    COALESCE(AVG(payment_value), 0)::NUMERIC(12,2)
        AS average_payment_value
FROM olist_bi.payments
GROUP BY payment_type
ORDER BY total_payment_value DESC;


-- ============================================================
-- 7. REVIEW ANALYTICS
-- ============================================================

CREATE OR REPLACE VIEW olist_bi.v_review_analytics AS
SELECT
    review_score,
    COUNT(*) AS review_count,
    ROUND(
        COUNT(*) * 100.0 /
        SUM(COUNT(*)) OVER (),
        2
    ) AS percentage
FROM olist_bi.reviews
GROUP BY review_score
ORDER BY review_score;


-- ============================================================
-- 8. DELIVERY PERFORMANCE
-- ============================================================

CREATE OR REPLACE VIEW olist_bi.v_delivery_performance AS
SELECT
    COUNT(*) FILTER (
        WHERE order_delivered_customer_date IS NOT NULL
    ) AS delivered_orders,

    COUNT(*) FILTER (
        WHERE
            order_delivered_customer_date IS NOT NULL
            AND order_estimated_delivery_date IS NOT NULL
            AND order_delivered_customer_date
                <= order_estimated_delivery_date
    ) AS on_time_orders,

    COUNT(*) FILTER (
        WHERE
            order_delivered_customer_date IS NOT NULL
            AND order_estimated_delivery_date IS NOT NULL
            AND order_delivered_customer_date
                > order_estimated_delivery_date
    ) AS late_orders,

    ROUND(
        AVG(
            EXTRACT(
                EPOCH FROM (
                    order_delivered_customer_date
                    - order_purchase_timestamp
                )
            ) / 86400
        )::NUMERIC,
        2
    ) AS average_delivery_days
FROM olist_bi.orders;


-- ============================================================
-- 9. PRODUCT ML INTELLIGENCE
-- ============================================================

CREATE OR REPLACE VIEW olist_bi.v_product_intelligence AS
SELECT
    pf.product_id,
    pf.forecast_month,
    pf.forecast_demand,
    pf.forecast_vs_3m_pct,

    pt.analysis_month,
    pt.trend,
    pt.trend_strength,

    pa.anomaly_flag,
    pa.anomaly_type,
    pa.anomaly_severity,

    ds.health_score,
    ds.health_status,
    ds.opportunity_score,
    ds.risk_score,
    ds.decision_priority,

    mr.recommendation
FROM olist_bi.product_forecasts pf
LEFT JOIN olist_bi.product_trends pt
    ON pf.product_id = pt.product_id
LEFT JOIN olist_bi.product_anomalies pa
    ON pf.product_id = pa.product_id
LEFT JOIN olist_bi.product_decision_scores ds
    ON pf.product_id = ds.product_id
LEFT JOIN olist_bi.management_recommendations mr
    ON pf.product_id = mr.product_id;


-- ============================================================
-- 10. OPPORTUNITY PRODUCTS
-- ============================================================

CREATE OR REPLACE VIEW olist_bi.v_product_opportunities AS
SELECT *
FROM olist_bi.v_product_intelligence
WHERE
    COALESCE(opportunity_score, 0) > 0
ORDER BY opportunity_score DESC;


-- ============================================================
-- 11. RISK PRODUCTS
-- ============================================================

CREATE OR REPLACE VIEW olist_bi.v_product_risks AS
SELECT *
FROM olist_bi.v_product_intelligence
WHERE
    COALESCE(risk_score, 0) > 0
ORDER BY risk_score DESC;


-- ============================================================
-- 12. ANOMALOUS PRODUCTS
-- ============================================================

CREATE OR REPLACE VIEW olist_bi.v_product_anomalies AS
SELECT *
FROM olist_bi.v_product_intelligence
WHERE
    COALESCE(anomaly_flag, 'normal') <> 'normal'
ORDER BY risk_score DESC NULLS LAST;


-- ============================================================
-- 13. DASHBOARD SUMMARY
-- ============================================================

CREATE OR REPLACE VIEW olist_bi.v_dashboard_summary AS
SELECT
    k.total_orders,
    k.delivered_orders,
    k.total_customers,
    k.total_products,
    k.total_sellers,
    k.total_revenue,
    k.average_order_value,

    (
        SELECT COUNT(*)
        FROM olist_bi.v_product_opportunities
    ) AS opportunity_products,

    (
        SELECT COUNT(*)
        FROM olist_bi.v_product_risks
    ) AS risk_products,

    (
        SELECT COUNT(*)
        FROM olist_bi.v_product_anomalies
    ) AS anomaly_products

FROM olist_bi.v_executive_kpis k;
