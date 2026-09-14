import os
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

SCHEMA_FILE = Path(__file__).with_name("olist_bi_schema.sql")
DATA_DIR = Path(os.getenv("OLIST_DATA_DIR", "/data/olist"))
OUTPUT_DIR = Path(os.getenv("OLIST_OUTPUT_DIR", "/data/ml_outputs"))
POSTGRES_URL = os.getenv("POSTGRES_URL")

if not POSTGRES_URL:
    raise RuntimeError("POSTGRES_URL is not set")

FILES = {
    "products": ["olist_products_dataset.csv", "olist_products_dataset(1).csv"],
    "order_items": ["olist_order_items_dataset.csv"],
    "geolocation": ["olist_geolocation_dataset.csv"],
    "customers": ["olist_customers_dataset.csv"],
    "category_translation": ["product_category_name_translation.csv", "product_category_name_translation(1).csv"],
    "payments": ["olist_order_payments_dataset.csv", "olist_order_payments_dataset(1).csv"],
    "orders": ["olist_orders_dataset.csv", "olist_orders_dataset(1).csv"],
    "reviews": ["olist_order_reviews_dataset.csv"],
    "sellers": ["olist_sellers_dataset.csv", "olist_sellers_dataset(1).csv"],
}

TABLE_MAP = {
    "products": "products",
    "order_items": "order_items",
    "geolocation": "geolocation",
    "customers": "customers",
    "category_translation": "category_translation",
    "payments": "payments",
    "orders": "orders",
    "reviews": "reviews",
    "sellers": "sellers",
}

DATE_COLUMNS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
}

ML_ANALYSIS_MONTH = os.getenv("ML_ANALYSIS_MONTH", "2018-08-01")
ML_FORECAST_MONTH = os.getenv("ML_FORECAST_MONTH", "2018-09-01")

ML_COLUMNS = {
    "product_trends": [
        "product_id", "analysis_month", "trend", "trend_strength"
    ],
    "product_anomalies": [
        "product_id", "analysis_month", "anomaly_flag",
        "anomaly_type", "anomaly_severity",
        "actual_demand", "expected_demand"
    ],
    "product_decision_scores": [
        "product_id", "analysis_month", "health_score",
        "health_status", "opportunity_score", "risk_score",
        "decision_priority", "volume_tier", "business_relevance"
    ],
    "management_recommendations": [
        "product_id", "analysis_month",
        "decision_priority", "recommendation"
    ],
}

def resolve_file(candidates):
    roots = [DATA_DIR, Path("/mnt/data"), Path.cwd()]
    for root in roots:
        for name in candidates:
            path = root / name
            if path.exists():
                return path
    raise FileNotFoundError(
        f"Could not find any of: {candidates}"
    )

def clean_columns(df):
    df.columns = [
        str(c).strip().lower().replace(" ", "_")
        for c in df.columns
    ]
    return df

def execute_schema(engine):
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    statements = [
        s.strip()
        for s in sql.split(";")
        if s.strip()
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))

def load_raw_table(engine, key):
    path = resolve_file(FILES[key])
    df = clean_columns(pd.read_csv(path))

    for col in DATE_COLUMNS.get(key, []):
        if col in df.columns:
            df[col] = pd.to_datetime(
                df[col], errors="coerce"
            )

    df = df.rename(columns={
        "product_name_lenght": "product_name_length",
        "product_description_lenght": "product_description_length",
    })

    table = TABLE_MAP[key]

    print(
        f"Loading {key:22s} "
        f"{len(df):>10,} rows <- {path.name}"
    )

    df.to_sql(
        table,
        engine,
        schema="olist_bi",
        if_exists="append",
        index=False,
        chunksize=5000,
        method="multi",
    )

def load_ml_csv(
    engine,
    filename,
    table,
    rename=None,
    snapshot=False
):
    path = OUTPUT_DIR / filename

    if not path.exists():
        print(f"ML output not found, skipping: {filename}")
        return

    df = pd.read_csv(path)
    df = clean_columns(df)

    if rename:
        df = df.rename(columns=rename)

    if snapshot and "analysis_month" not in df.columns:
        df["analysis_month"] = pd.Timestamp(
            ML_ANALYSIS_MONTH
        ).date()

    keep = [
        c for c in ML_COLUMNS[table]
        if c in df.columns
    ]

    df = df[keep].copy()

    required = {
        "product_trends": [
            "product_id",
            "analysis_month",
            "trend",
            "trend_strength",
        ],
        "product_anomalies": [
            "product_id",
            "analysis_month",
        ],
        "product_decision_scores": [
            "product_id",
            "analysis_month",
        ],
        "management_recommendations": [
            "product_id",
            "analysis_month",
        ],
    }[table]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{filename} -> {table} missing columns: "
            f"{missing}. Available: {list(pd.read_csv(path, nrows=0).columns)}"
        )

    null_required = [
        c for c in required
        if df[c].isna().any()
    ]

    if null_required:
        raise ValueError(
            f"{filename} contains NULL values in required columns: "
            f"{null_required}"
        )

    if "analysis_month" in df.columns:
        df["analysis_month"] = pd.to_datetime(
            df["analysis_month"],
            errors="coerce"
        ).dt.date

    print(
        f"Loading ML {table:26s} "
        f"{len(df):>10,} rows <- {filename}"
    )

    df.to_sql(
        table,
        engine,
        schema="olist_bi",
        if_exists="append",
        index=False,
        chunksize=5000,
        method="multi",
    )

def load_forecasts_from_master(engine):
    path = (
        OUTPUT_DIR /
        "product_management_master_phase3_7_final.csv"
    )

    if not path.exists():
        print(
            "ML output not found, skipping forecast master:",
            path.name
        )
        return

    df = clean_columns(pd.read_csv(path))

    required = [
        "product_id",
        "forecast_demand",
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Forecast master missing columns: {missing}"
        )

    out = pd.DataFrame({
        "product_id": df["product_id"],
        "forecast_month": pd.Timestamp(
            ML_FORECAST_MONTH
        ).date(),
        "forecast_demand": df["forecast_demand"],
        "forecast_growth_pct": None,
        "forecast_vs_3m_pct": (
            df["forecast_vs_3m_pct"]
            if "forecast_vs_3m_pct" in df.columns
            else None
        ),
        "model_name": "XGBoost",
    })

    out = out.dropna(
        subset=["product_id", "forecast_demand"]
    )

    print(
        f"Loading ML product_forecasts "
        f"{len(out):>10,} rows <- {path.name}"
    )

    out.to_sql(
        "product_forecasts",
        engine,
        schema="olist_bi",
        if_exists="append",
        index=False,
        chunksize=5000,
        method="multi",
    )

def main():
    engine = create_engine(
        POSTGRES_URL,
        pool_pre_ping=True
    )

    print("\n=== 1. Creating schema ===")
    execute_schema(engine)

    print("\n=== 2. Loading raw Olist data ===")

    for key in FILES:
        load_raw_table(engine, key)

    print("\n=== 3. Loading Phase 3.7 ML intelligence ===")

    load_forecasts_from_master(engine)

    load_ml_csv(
        engine,
        "product_calibrated_trends_phase3_7_final.csv",
        "product_trends",
        rename={"growth_signal": "trend"},
        snapshot=True,
    )

    load_ml_csv(
        engine,
        "product_anomaly_decision_risk_phase3_7_final.csv",
        "product_anomalies",
        snapshot=True,
    )

    load_ml_csv(
        engine,
        "product_decision_scores_phase3_7_final.csv",
        "product_decision_scores",
        snapshot=True,
    )

    load_ml_csv(
        engine,
        "management_recommendations_phase3_7_final.csv",
        "management_recommendations",
        rename={
            "recommendation_priority":
            "decision_priority"
        },
        snapshot=True,
    )

    print("\n=== 4. Row-count verification ===")

    tables = list(TABLE_MAP.values()) + [
        "product_forecasts",
        "product_trends",
        "product_anomalies",
        "product_decision_scores",
        "management_recommendations",
    ]

    with engine.connect() as conn:
        for table in tables:
            count = conn.execute(
                text(
                    f'SELECT COUNT(*) '
                    f'FROM olist_bi."{table}"'
                )
            ).scalar_one()

            print(
                f"{table:32s} {count:>12,}"
            )

    print("\n=== ETL COMPLETE ===")

if __name__ == "__main__":
    main()
