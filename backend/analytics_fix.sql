DROP VIEW IF EXISTS olist_bi.v_dashboard_summary CASCADE;

CREATE VIEW olist_bi.v_dashboard_summary AS
SELECT
    e.total_orders,
    e.delivered_orders,
    e.total_customers,
    e.total_products,
    e.total_sellers,
    e.total_revenue,
    e.average_order_value,

    (SELECT COUNT(*)
     FROM olist_bi.product_decision_scores
     WHERE decision_priority IN ('high_opportunity','opportunity')
    ) AS opportunity_products,

    (SELECT COUNT(*)
     FROM olist_bi.product_decision_scores
     WHERE decision_priority = 'high_opportunity'
    ) AS high_opportunity_products,

    (SELECT COUNT(*)
     FROM olist_bi.product_decision_scores
     WHERE decision_priority = 'opportunity'
    ) AS normal_opportunity_products,

    (SELECT COUNT(*)
     FROM olist_bi.product_decision_scores
     WHERE decision_priority = 'high_risk'
    ) AS high_risk_products,

    (SELECT COUNT(*)
     FROM olist_bi.product_decision_scores
     WHERE decision_priority = 'low_volume_risk'
    ) AS low_volume_risk_products,

    (SELECT COUNT(*)
     FROM olist_bi.product_decision_scores
     WHERE decision_priority = 'watch'
    ) AS watch_products,

    (SELECT COUNT(*)
     FROM olist_bi.product_decision_scores
     WHERE health_status = 'at_risk'
    ) AS at_risk_products,

    (SELECT COUNT(*)
     FROM olist_bi.product_decision_scores
     WHERE health_status = 'critical'
    ) AS critical_products,

    (SELECT COUNT(*)
     FROM olist_bi.v_product_anomalies
    ) AS anomaly_products

FROM olist_bi.v_executive_kpis e;
