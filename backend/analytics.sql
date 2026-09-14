-- BUSINESS KPI FIX
-- Delivered orders only for business sales/revenue metrics.

CREATE OR REPLACE VIEW olist_bi.v_executive_kpis AS
WITH delivered_orders AS (
    SELECT order_id, customer_id
    FROM olist_bi.orders
    WHERE order_status = 'delivered'
),
sales AS (
    SELECT
        COUNT(DISTINCT d.order_id) AS total_orders,
        COALESCE(SUM(oi.price), 0)::NUMERIC(14,2) AS total_revenue
    FROM delivered_orders d
    JOIN olist_bi.order_items oi
        ON oi.order_id = d.order_id
)
SELECT
    s.total_orders,
    (SELECT COUNT(*) FROM delivered_orders) AS delivered_orders,
    (
        SELECT COUNT(DISTINCT c.customer_unique_id)
        FROM delivered_orders d
        JOIN olist_bi.customers c
            ON c.customer_id = d.customer_id
    ) AS total_customers,
    (SELECT COUNT(*) FROM olist_bi.products) AS total_products,
    (SELECT COUNT(*) FROM olist_bi.sellers) AS total_sellers,
    s.total_revenue,
    CASE
        WHEN s.total_orders > 0
        THEN (s.total_revenue / s.total_orders)::NUMERIC(14,2)
        ELSE 0
    END AS average_order_value
FROM sales s;


CREATE OR REPLACE VIEW olist_bi.v_monthly_sales AS
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', o.order_purchase_timestamp)::DATE AS month,
        COUNT(DISTINCT o.order_id) AS orders,
        COALESCE(SUM(oi.price), 0)::NUMERIC(14,2) AS revenue
    FROM olist_bi.orders o
    JOIN olist_bi.order_items oi
        ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY 1
),
with_previous AS (
    SELECT
        *,
        LAG(revenue) OVER (ORDER BY month) AS previous_revenue
    FROM monthly
)
SELECT
    month,
    orders,
    revenue,
    CASE
        WHEN previous_revenue IS NULL OR previous_revenue = 0
        THEN NULL
        ELSE (
            (revenue - previous_revenue)
            / previous_revenue * 100
        )::NUMERIC(10,2)
    END AS revenue_growth_pct
FROM with_previous
ORDER BY month;


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
JOIN olist_bi.orders o
    ON o.order_id = oi.order_id
   AND o.order_status = 'delivered'
LEFT JOIN olist_bi.category_translation ct
    ON p.product_category_name = ct.product_category_name
GROUP BY
    p.product_id,
    ct.product_category_name_english,
    p.product_category_name
ORDER BY revenue DESC;


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
JOIN olist_bi.orders o
    ON o.order_id = oi.order_id
   AND o.order_status = 'delivered'
JOIN olist_bi.products p
    ON oi.product_id = p.product_id
LEFT JOIN olist_bi.category_translation ct
    ON p.product_category_name = ct.product_category_name
GROUP BY
    ct.product_category_name_english,
    p.product_category_name
ORDER BY revenue DESC;


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
JOIN olist_bi.orders o
    ON o.order_id = oi.order_id
   AND o.order_status = 'delivered'
GROUP BY
    s.seller_id,
    s.seller_city,
    s.seller_state
ORDER BY revenue DESC;


-- PRODUCT INTELLIGENCE
-- Always use the latest available ML snapshot per product.
CREATE OR REPLACE VIEW olist_bi.v_product_intelligence AS
WITH latest_forecast AS (
    SELECT *
    FROM (
        SELECT
            pf.*,
            ROW_NUMBER() OVER (
                PARTITION BY product_id
                ORDER BY forecast_month DESC, created_at DESC
            ) AS rn
        FROM olist_bi.product_forecasts pf
    ) x
    WHERE rn = 1
),
latest_trend AS (
    SELECT *
    FROM (
        SELECT
            pt.*,
            ROW_NUMBER() OVER (
                PARTITION BY product_id
                ORDER BY analysis_month DESC, created_at DESC
            ) AS rn
        FROM olist_bi.product_trends pt
    ) x
    WHERE rn = 1
),
latest_anomaly AS (
    SELECT *
    FROM (
        SELECT
            pa.*,
            ROW_NUMBER() OVER (
                PARTITION BY product_id
                ORDER BY analysis_month DESC, created_at DESC
            ) AS rn
        FROM olist_bi.product_anomalies pa
    ) x
    WHERE rn = 1
),
latest_decision AS (
    SELECT *
    FROM (
        SELECT
            ds.*,
            ROW_NUMBER() OVER (
                PARTITION BY product_id
                ORDER BY analysis_month DESC, created_at DESC
            ) AS rn
        FROM olist_bi.product_decision_scores ds
    ) x
    WHERE rn = 1
),
latest_recommendation AS (
    SELECT *
    FROM (
        SELECT
            mr.*,
            ROW_NUMBER() OVER (
                PARTITION BY product_id
                ORDER BY analysis_month DESC, created_at DESC
            ) AS rn
        FROM olist_bi.management_recommendations mr
    ) x
    WHERE rn = 1
)
SELECT
    pf.product_id,
    COALESCE(
        ct.product_category_name_english,
        p.product_category_name,
        'unknown'
    ) AS category,

    pf.forecast_month,
    pf.forecast_demand,
    pf.forecast_growth_pct,
    pf.forecast_vs_3m_pct,

    pt.analysis_month,
    pt.trend,
    pt.trend_strength,

    pa.anomaly_flag,
    pa.anomaly_type,
    pa.anomaly_severity,
    pa.actual_demand,
    pa.expected_demand,

    ds.health_score,
    ds.health_status,
    ds.opportunity_score,
    ds.risk_score,
    ds.decision_priority,
    ds.volume_tier,
    ds.business_relevance,

    mr.recommendation

FROM latest_forecast pf

LEFT JOIN latest_trend pt
    ON pf.product_id = pt.product_id

LEFT JOIN latest_anomaly pa
    ON pf.product_id = pa.product_id

LEFT JOIN latest_decision ds
    ON pf.product_id = ds.product_id

LEFT JOIN latest_recommendation mr
    ON pf.product_id = mr.product_id

LEFT JOIN olist_bi.products p
    ON p.product_id = pf.product_id

LEFT JOIN olist_bi.category_translation ct
    ON ct.product_category_name = p.product_category_name;


-- FINAL DECISION LOGIC

CREATE OR REPLACE VIEW olist_bi.v_product_opportunities AS
SELECT *
FROM olist_bi.v_product_intelligence
WHERE decision_priority IN (
    'high_opportunity',
    'opportunity'
)
ORDER BY opportunity_score DESC NULLS LAST;


CREATE OR REPLACE VIEW olist_bi.v_product_risks AS
SELECT *
FROM olist_bi.v_product_intelligence
WHERE decision_priority IN (
    'high_risk',
    'low_volume_risk',
    'watch'
)
OR health_status IN (
    'at_risk',
    'critical'
)
ORDER BY risk_score DESC NULLS LAST;


CREATE OR REPLACE VIEW olist_bi.v_product_anomalies AS
SELECT *
FROM olist_bi.v_product_intelligence
WHERE COALESCE(anomaly_flag, 'normal') <> 'normal'
ORDER BY anomaly_severity DESC NULLS LAST;


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
        FROM olist_bi.v_product_opportunities
        WHERE decision_priority = 'high_opportunity'
    ) AS high_opportunity_products,

    (
        SELECT COUNT(*)
        FROM olist_bi.v_product_opportunities
        WHERE decision_priority = 'opportunity'
    ) AS normal_opportunity_products,

    (
        SELECT COUNT(*)
        FROM olist_bi.v_product_risks
        WHERE decision_priority = 'high_risk'
    ) AS high_risk_products,

    (
        SELECT COUNT(*)
        FROM olist_bi.v_product_risks
        WHERE decision_priority = 'low_volume_risk'
    ) AS low_volume_risk_products,

    (
        SELECT COUNT(*)
        FROM olist_bi.v_product_risks
        WHERE decision_priority = 'watch'
    ) AS watch_products,

    (
        SELECT COUNT(*)
        FROM olist_bi.v_product_intelligence
        WHERE health_status = 'at_risk'
    ) AS at_risk_products,

    (
        SELECT COUNT(*)
        FROM olist_bi.v_product_intelligence
        WHERE health_status = 'critical'
    ) AS critical_products,

    (
        SELECT COUNT(*)
        FROM olist_bi.v_product_anomalies
    ) AS anomaly_products

FROM olist_bi.v_executive_kpis k;
