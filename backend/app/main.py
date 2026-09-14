import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from app.query_router import route_query
from app.sql_engine import execute_sql_query
from app.ml_engine import execute_ml_query
from app.rag_engine import execute_rag_query
from app.ai_analyst import build_business_answer

DATABASE_URL = os.environ["POSTGRES_URL"]

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
)

app = FastAPI(
    title="Olist AI Business Intelligence API",
    version="0.2.0",
    description="Analytics, ML intelligence and decision-support API for Olist e-commerce data."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def fetch_all(sql, params=None):
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params or {}).mappings().all()
    return [dict(row) for row in rows]


def fetch_one(sql, params=None):
    with engine.connect() as conn:
        row = conn.execute(text(sql), params or {}).mappings().first()
    return dict(row) if row else None


@app.get("/")
def root():
    return {
        "name": "Olist AI Business Intelligence API",
        "version": "0.2.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ---------------------------------------------------------
# EXECUTIVE
# ---------------------------------------------------------

@app.get("/api/v1/kpis")
def kpis():
    sql = """
    SELECT
        COUNT(DISTINCT o.order_id)
            FILTER (WHERE o.order_status = 'delivered') AS orders,

        COUNT(DISTINCT oi.product_id)
            FILTER (WHERE o.order_status = 'delivered') AS products,

        COUNT(DISTINCT oi.seller_id)
            FILTER (WHERE o.order_status = 'delivered') AS sellers,

        COUNT(DISTINCT o.customer_id)
            FILTER (WHERE o.order_status = 'delivered') AS customers,

        COALESCE(
            SUM(oi.price + oi.freight_value)
            FILTER (WHERE o.order_status = 'delivered'),
            0
        ) AS gross_sales,

        COALESCE(
            SUM(oi.price)
            FILTER (WHERE o.order_status = 'delivered'),
            0
        ) AS product_revenue

    FROM olist_bi.orders o
    LEFT JOIN olist_bi.order_items oi
        ON oi.order_id = o.order_id
    """

    result = fetch_one(sql)

    orders = int(result["orders"] or 0)
    gross_sales = float(result["gross_sales"] or 0)

    result["aov"] = gross_sales / orders if orders else 0

    return result


@app.get("/api/v1/dashboard/summary")
def dashboard_summary():
    sql = """
    SELECT
        *
    FROM olist_bi.v_dashboard_summary
    """

    row = fetch_one(sql)

    if not row:
        raise HTTPException(404, "Dashboard summary unavailable")

    return row


# ---------------------------------------------------------
# SALES
# ---------------------------------------------------------

@app.get("/api/v1/sales/monthly")
def monthly_sales():
    return {
        "items": fetch_all("""
            SELECT *
            FROM olist_bi.v_monthly_sales
            ORDER BY month
        """)
    }


@app.get("/api/v1/sales/categories")
def category_sales(
    limit: int = Query(50, ge=1, le=500)
):
    return {
        "items": fetch_all("""
            SELECT *
            FROM olist_bi.v_category_performance
            ORDER BY revenue DESC
            LIMIT :limit
        """, {"limit": limit})
    }


# ---------------------------------------------------------
# PRODUCTS
# ---------------------------------------------------------

@app.get("/api/v1/products")
def products(
    limit: int = Query(50, ge=1, le=500),
    category: Optional[str] = None
):
    sql = """
    SELECT
        p.product_id,
        COALESCE(
            ct.product_category_name_english,
            p.product_category_name,
            'unknown'
        ) AS category,

        COUNT(DISTINCT oi.order_id) AS orders,
        COUNT(*) AS units,
        COALESCE(SUM(oi.price), 0) AS revenue

    FROM olist_bi.products p

    LEFT JOIN olist_bi.category_translation ct
        ON ct.product_category_name = p.product_category_name

    LEFT JOIN olist_bi.order_items oi
        ON oi.product_id = p.product_id

    LEFT JOIN olist_bi.orders o
        ON o.order_id = oi.order_id

    WHERE
        (
            :category IS NULL
            OR COALESCE(
                ct.product_category_name_english,
                p.product_category_name,
                'unknown'
            ) = :category
        )
        AND (
            o.order_status = 'delivered'
            OR o.order_status IS NULL
        )

    GROUP BY p.product_id, category

    ORDER BY revenue DESC

    LIMIT :limit
    """

    rows = fetch_all(
        sql,
        {
            "limit": limit,
            "category": category
        }
    )

    return {
        "items": rows,
        "count": len(rows)
    }


@app.get("/api/v1/products/top")
def top_products(
    limit: int = Query(20, ge=1, le=100)
):
    rows = fetch_all("""
        SELECT *
        FROM olist_bi.v_top_products
        ORDER BY revenue DESC
        LIMIT :limit
    """, {"limit": limit})

    return {
        "items": rows,
        "count": len(rows)
    }


@app.get("/api/v1/products/{product_id}/intelligence")
def product_intelligence(product_id: str):

    sql = """
    SELECT
        p.product_id,

        COALESCE(
            ct.product_category_name_english,
            p.product_category_name,
            'unknown'
        ) AS category,

        f.forecast_month,
        f.forecast_demand,
        f.forecast_growth_pct,
        f.forecast_vs_3m_pct,

        t.trend,
        t.trend_strength,

        a.anomaly_flag,
        a.anomaly_type,
        a.anomaly_severity,
        a.actual_demand,
        a.expected_demand,

        d.health_score,
        d.health_status,
        d.opportunity_score,
        d.risk_score,
        d.decision_priority,
        d.volume_tier,
        d.business_relevance,

        r.recommendation

    FROM olist_bi.products p

    LEFT JOIN olist_bi.category_translation ct
        ON ct.product_category_name = p.product_category_name

    LEFT JOIN LATERAL (
        SELECT *
        FROM olist_bi.product_forecasts
        WHERE product_id = p.product_id
        ORDER BY forecast_month DESC
        LIMIT 1
    ) f ON TRUE

    LEFT JOIN LATERAL (
        SELECT *
        FROM olist_bi.product_trends
        WHERE product_id = p.product_id
        ORDER BY analysis_month DESC
        LIMIT 1
    ) t ON TRUE

    LEFT JOIN LATERAL (
        SELECT *
        FROM olist_bi.product_anomalies
        WHERE product_id = p.product_id
        ORDER BY analysis_month DESC
        LIMIT 1
    ) a ON TRUE

    LEFT JOIN LATERAL (
        SELECT *
        FROM olist_bi.product_decision_scores
        WHERE product_id = p.product_id
        ORDER BY analysis_month DESC
        LIMIT 1
    ) d ON TRUE

    LEFT JOIN LATERAL (
        SELECT *
        FROM olist_bi.management_recommendations
        WHERE product_id = p.product_id
        ORDER BY analysis_month DESC
        LIMIT 1
    ) r ON TRUE

    WHERE p.product_id = :product_id
    """

    row = fetch_one(sql, {"product_id": product_id})

    if not row:
        raise HTTPException(404, "Product not found")

    return row


# ---------------------------------------------------------
# ML FORECAST
# ---------------------------------------------------------

@app.get("/api/v1/forecast")
def forecast(
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = None
):
    sql = """
    SELECT
        f.product_id,
        COALESCE(
            ct.product_category_name_english,
            p.product_category_name,
            'unknown'
        ) AS category,

        f.forecast_month,
        f.forecast_demand,
        f.forecast_growth_pct,
        f.forecast_vs_3m_pct

    FROM olist_bi.product_forecasts f

    LEFT JOIN olist_bi.products p
        ON p.product_id = f.product_id

    LEFT JOIN olist_bi.category_translation ct
        ON ct.product_category_name = p.product_category_name

    WHERE
        (
            :category IS NULL
            OR COALESCE(
                ct.product_category_name_english,
                p.product_category_name,
                'unknown'
            ) = :category
        )

    ORDER BY f.forecast_demand DESC

    LIMIT :limit
    """

    rows = fetch_all(
        sql,
        {
            "limit": limit,
            "category": category
        }
    )

    return {
        "items": rows,
        "count": len(rows)
    }


# ---------------------------------------------------------
# ANOMALIES
# ---------------------------------------------------------

@app.get("/api/v1/anomalies")
def anomalies(
    severity: Optional[float] = Query(None, ge=0, le=100),
    limit: int = Query(50, ge=1, le=500)
):
    sql = """
    SELECT
        a.*,
        COALESCE(
            ct.product_category_name_english,
            p.product_category_name,
            'unknown'
        ) AS category

    FROM olist_bi.product_anomalies a

    LEFT JOIN olist_bi.products p
        ON p.product_id = a.product_id

    LEFT JOIN olist_bi.category_translation ct
        ON ct.product_category_name = p.product_category_name

    WHERE
        (:severity IS NULL OR a.anomaly_severity >= :severity)

    ORDER BY
        a.anomaly_severity DESC NULLS LAST,
        a.analysis_month DESC

    LIMIT :limit
    """

    rows = fetch_all(
        sql,
        {
            "severity": severity,
            "limit": limit
        }
    )

    return {
        "items": rows,
        "count": len(rows)
    }


# ---------------------------------------------------------
# DECISION SUPPORT
# ---------------------------------------------------------

@app.get("/api/v1/decisions")
def decisions(
    priority: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    sql = """
    SELECT
        d.*,
        COALESCE(
            ct.product_category_name_english,
            p.product_category_name,
            'unknown'
        ) AS category

    FROM olist_bi.product_decision_scores d

    LEFT JOIN olist_bi.products p
        ON p.product_id = d.product_id

    LEFT JOIN olist_bi.category_translation ct
        ON ct.product_category_name = p.product_category_name

    WHERE
        (:priority IS NULL OR d.decision_priority = :priority)

    ORDER BY
        d.opportunity_score DESC,
        d.risk_score DESC

    LIMIT :limit
    """

    rows = fetch_all(
        sql,
        {
            "priority": priority,
            "limit": limit
        }
    )

    return {
        "items": rows,
        "count": len(rows)
    }


@app.get("/api/v1/opportunities")
def opportunities(
    limit: int = Query(100, ge=1, le=1000)
):
    rows = fetch_all("""
        SELECT *
        FROM olist_bi.v_product_opportunities
        ORDER BY opportunity_score DESC
        LIMIT :limit
    """, {"limit": limit})

    return {
        "items": rows,
        "count": len(rows)
    }


@app.get("/api/v1/risks")
def risks(
    limit: int = Query(100, ge=1, le=1000)
):
    rows = fetch_all("""
        SELECT *
        FROM olist_bi.v_product_risks
        ORDER BY risk_score DESC
        LIMIT :limit
    """, {"limit": limit})

    return {
        "items": rows,
        "count": len(rows)
    }


@app.get("/api/v1/recommendations")
def recommendations(
    limit: int = Query(100, ge=1, le=1000)
):
    rows = fetch_all("""
        SELECT
            r.*,
            COALESCE(
                ct.product_category_name_english,
                p.product_category_name,
                'unknown'
            ) AS category

        FROM olist_bi.management_recommendations r

        LEFT JOIN olist_bi.products p
            ON p.product_id = r.product_id

        LEFT JOIN olist_bi.category_translation ct
            ON ct.product_category_name = p.product_category_name

        ORDER BY r.analysis_month DESC, r.product_id

        LIMIT :limit
    """, {"limit": limit})

    return {
        "items": rows,
        "count": len(rows)
    }


# ---------------------------------------------------------
# SELLERS
# ---------------------------------------------------------

@app.get("/api/v1/sellers")
def sellers(
    limit: int = Query(50, ge=1, le=500)
):
    rows = fetch_all("""
        SELECT *
        FROM olist_bi.v_seller_performance
        ORDER BY revenue DESC
        LIMIT :limit
    """, {"limit": limit})

    return {
        "items": rows,
        "count": len(rows)
    }


# ---------------------------------------------------------
# REVIEWS / PAYMENTS / DELIVERY
# ---------------------------------------------------------

@app.get("/api/v1/reviews")
def reviews(
    limit: int = Query(50, ge=1, le=500)
):
    rows = fetch_all("""
        SELECT *
        FROM olist_bi.v_review_analytics
        LIMIT :limit
    """, {"limit": limit})

    return {
        "items": rows,
        "count": len(rows)
    }


@app.get("/api/v1/payments")
def payments():
    return {
        "items": fetch_all("""
            SELECT *
            FROM olist_bi.v_payment_analytics
        """)
    }


@app.get("/api/v1/delivery")
def delivery():
    return {
        "items": fetch_all("""
            SELECT *
            FROM olist_bi.v_delivery_performance
        """)
    }


# ---------------------------------------------------------
# CATEGORIES
# ---------------------------------------------------------

@app.get("/api/v1/categories")
def categories():
    rows = fetch_all("""
        SELECT *
        FROM olist_bi.v_category_performance
        ORDER BY revenue DESC
    """)

    return {
        "items": rows,
        "count": len(rows)
    }

@app.get("/api/v1/query/route")
def query_route(
    q: str = Query(..., min_length=1, max_length=1000)
):
    route = route_query(q)

    return {
        "query": q,
        "route": route.value
    }

@app.get("/api/v1/query/sql")
def query_sql(
    q: str = Query(..., min_length=1, max_length=1000),
    limit: int = Query(10, ge=1, le=100)
):
    try:
        return execute_sql_query(
            engine=engine,
            query=q,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/api/v1/query/ml")
def query_ml(
    q: str = Query(..., min_length=1, max_length=1000),
    limit: int = Query(10, ge=1, le=100)
):
    try:
        return execute_ml_query(
            engine=engine,
            query=q,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/query")
def unified_query(
    q: str = Query(..., min_length=1, max_length=1000),
    limit: int = Query(10, ge=1, le=100)
):
    route = route_query(q)

    if route.value == "sql":
        result = execute_sql_query(engine, q, limit)
    elif route.value == "ml":
        result = execute_ml_query(engine, q, limit)
    else:
        result = {
            "source": "router",
            "route": route.value,
            "message": "This query requires multiple intelligence sources."
        }

    return {
        "query": q,
        "route": route.value,
        "result": result
    }

@app.get("/api/v1/query/rag")
def query_rag(
    q: str = Query(..., min_length=1, max_length=1000)
):
    try:
        return execute_rag_query(q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/v1/analyst')
def analyst_query(q: str = Query(..., min_length=1, max_length=1000), limit: int = Query(10, ge=1, le=100)):
    try:
        route = route_query(q)
        sql_result = None
        ml_result = None
        rag_result = None
        if route.value in ['sql', 'sql_ml', 'sql_ml_rag']:
            sql_result = execute_sql_query(engine, q, limit)
        if route.value in ['ml', 'sql_ml', 'sql_ml_rag']:
            ml_result = execute_ml_query(engine, q, limit)
        if route.value in ['rag', 'sql_ml_rag']:
            rag_result = execute_rag_query(q)
        return build_business_answer(query=q, sql_result=sql_result, ml_result=ml_result, rag_result=rag_result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


