-- Olist AI Business Intelligence — PostgreSQL schema
-- Phase 4.1: transactional + analytics + ML intelligence tables

CREATE SCHEMA IF NOT EXISTS olist_bi;

-- Core dimensions / facts
CREATE TABLE IF NOT EXISTS olist_bi.products (
    product_id TEXT PRIMARY KEY,
    product_category_name TEXT,
    product_name_length INTEGER,
    product_description_length INTEGER,
    product_photos_qty INTEGER,
    product_weight_g DOUBLE PRECISION,
    product_length_cm DOUBLE PRECISION,
    product_height_cm DOUBLE PRECISION,
    product_width_cm DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS olist_bi.sellers (
    seller_id TEXT PRIMARY KEY,
    seller_zip_code_prefix INTEGER,
    seller_city TEXT,
    seller_state TEXT
);

CREATE TABLE IF NOT EXISTS olist_bi.customers (
    customer_id TEXT PRIMARY KEY,
    customer_unique_id TEXT,
    customer_zip_code_prefix INTEGER,
    customer_city TEXT,
    customer_state TEXT
);

CREATE TABLE IF NOT EXISTS olist_bi.orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT,
    order_status TEXT,
    order_purchase_timestamp TIMESTAMP,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS olist_bi.order_items (
    order_id TEXT,
    order_item_id INTEGER,
    product_id TEXT,
    seller_id TEXT,
    shipping_limit_date TIMESTAMP,
    price NUMERIC(12,2),
    freight_value NUMERIC(12,2),
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE IF NOT EXISTS olist_bi.payments (
    order_id TEXT,
    payment_sequential INTEGER,
    payment_type TEXT,
    payment_installments INTEGER,
    payment_value NUMERIC(12,2),
    PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE IF NOT EXISTS olist_bi.reviews (
    review_record_id BIGSERIAL PRIMARY KEY,
    review_id TEXT,
    order_id TEXT,
    review_score INTEGER,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS olist_bi.geolocation (
    geolocation_zip_code_prefix INTEGER,
    geolocation_lat DOUBLE PRECISION,
    geolocation_lng DOUBLE PRECISION,
    geolocation_city TEXT,
    geolocation_state TEXT
);

CREATE TABLE IF NOT EXISTS olist_bi.category_translation (
    product_category_name TEXT PRIMARY KEY,
    product_category_name_english TEXT
);

-- ML intelligence tables
CREATE TABLE IF NOT EXISTS olist_bi.product_forecasts (
    product_id TEXT,
    forecast_month DATE,
    forecast_demand DOUBLE PRECISION,
    forecast_growth_pct DOUBLE PRECISION,
    forecast_vs_3m_pct DOUBLE PRECISION,
    model_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id, forecast_month)
);

CREATE TABLE IF NOT EXISTS olist_bi.product_trends (
    product_id TEXT,
    analysis_month DATE,
    trend TEXT,
    trend_strength DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id, analysis_month)
);

CREATE TABLE IF NOT EXISTS olist_bi.product_anomalies (
    product_id TEXT,
    analysis_month DATE,
    anomaly_flag TEXT,
    anomaly_type TEXT,
    anomaly_severity DOUBLE PRECISION,
    actual_demand DOUBLE PRECISION,
    expected_demand DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id, analysis_month)
);

CREATE TABLE IF NOT EXISTS olist_bi.product_decision_scores (
    product_id TEXT,
    analysis_month DATE,
    health_score DOUBLE PRECISION,
    health_status TEXT,
    opportunity_score DOUBLE PRECISION,
    risk_score DOUBLE PRECISION,
    decision_priority TEXT,
    volume_tier TEXT,
    business_relevance DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id, analysis_month)
);

CREATE TABLE IF NOT EXISTS olist_bi.management_recommendations (
    product_id TEXT,
    analysis_month DATE,
    decision_priority TEXT,
    recommendation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id, analysis_month)
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_reviews_review_id
    ON olist_bi.reviews(review_id);

CREATE INDEX IF NOT EXISTS idx_reviews_order_id
    ON olist_bi.reviews(order_id);

CREATE INDEX IF NOT EXISTS idx_orders_purchase_ts
    ON olist_bi.orders(order_purchase_timestamp);

CREATE INDEX IF NOT EXISTS idx_orders_status
    ON olist_bi.orders(order_status);

CREATE INDEX IF NOT EXISTS idx_order_items_product
    ON olist_bi.order_items(product_id);

CREATE INDEX IF NOT EXISTS idx_order_items_seller
    ON olist_bi.order_items(seller_id);

CREATE INDEX IF NOT EXISTS idx_customers_state
    ON olist_bi.customers(customer_state);

CREATE INDEX IF NOT EXISTS idx_sellers_state
    ON olist_bi.sellers(seller_state);

CREATE INDEX IF NOT EXISTS idx_forecasts_month
    ON olist_bi.product_forecasts(forecast_month);

CREATE INDEX IF NOT EXISTS idx_anomalies_severity
    ON olist_bi.product_anomalies(anomaly_severity);

CREATE INDEX IF NOT EXISTS idx_decision_priority
    ON olist_bi.product_decision_scores(decision_priority);
