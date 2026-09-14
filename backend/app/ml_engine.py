from typing import Dict, Any

from sqlalchemy import text


ML_INTENTS = {
    "forecast": """
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
        ORDER BY f.forecast_demand DESC
        LIMIT :limit
    """,

    "growth": """
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
        ORDER BY f.forecast_vs_3m_pct DESC NULLS LAST
        LIMIT :limit
    """,

    "trend": """
        SELECT
            t.product_id,
            COALESCE(
                ct.product_category_name_english,
                p.product_category_name,
                'unknown'
            ) AS category,
            t.analysis_month,
            t.trend,
            t.trend_strength,
            t.forecast_vs_3m_pct,
            t.forecast_delta_vs_3m
        FROM olist_bi.product_trends t
        LEFT JOIN olist_bi.products p
            ON p.product_id = t.product_id
        LEFT JOIN olist_bi.category_translation ct
            ON ct.product_category_name = p.product_category_name
        ORDER BY ABS(t.forecast_vs_3m_pct) DESC NULLS LAST
        LIMIT :limit
    """,

    "opportunity": """
        SELECT
            d.product_id,
            COALESCE(
                ct.product_category_name_english,
                p.product_category_name,
                'unknown'
            ) AS category,
            d.health_score,
            d.health_status,
            d.opportunity_score,
            d.risk_score,
            d.decision_priority,
            d.business_relevance
        FROM olist_bi.product_decision_scores d
        LEFT JOIN olist_bi.products p
            ON p.product_id = d.product_id
        LEFT JOIN olist_bi.category_translation ct
            ON ct.product_category_name = p.product_category_name
        WHERE d.decision_priority IN ('high_opportunity', 'opportunity')
        ORDER BY d.opportunity_score DESC
        LIMIT :limit
    """,

    "risk": """
        SELECT
            d.product_id,
            COALESCE(
                ct.product_category_name_english,
                p.product_category_name,
                'unknown'
            ) AS category,
            d.health_score,
            d.health_status,
            d.opportunity_score,
            d.risk_score,
            d.decision_priority,
            d.business_relevance
        FROM olist_bi.product_decision_scores d
        LEFT JOIN olist_bi.products p
            ON p.product_id = d.product_id
        LEFT JOIN olist_bi.category_translation ct
            ON ct.product_category_name = p.product_category_name
        WHERE d.decision_priority IN (
            'high_risk',
            'low_volume_risk',
            'watch'
        )
        OR d.health_status IN ('at_risk', 'critical')
        ORDER BY d.risk_score DESC
        LIMIT :limit
    """,

    "anomaly": """
        SELECT
            a.product_id,
            COALESCE(
                ct.product_category_name_english,
                p.product_category_name,
                'unknown'
            ) AS category,
            a.analysis_month,
            a.anomaly_flag,
            a.anomaly_type,
            a.anomaly_severity,
            a.actual_demand,
            a.expected_demand
        FROM olist_bi.product_anomalies a
        LEFT JOIN olist_bi.products p
            ON p.product_id = a.product_id
        LEFT JOIN olist_bi.category_translation ct
            ON ct.product_category_name = p.product_category_name
        WHERE a.anomaly_flag != 'normal'
        ORDER BY a.anomaly_severity DESC NULLS LAST
        LIMIT :limit
    """
}


def detect_ml_intent(query: str) -> str:
    q = query.lower()

    if any(x in q for x in [
        "anomaly",
        "anomalies",
        "unusual",
        "abnormal"
    ]):
        return "anomaly"

    if any(x in q for x in [
        "risk",
        "risky",
        "at risk",
        "critical"
    ]):
        return "risk"

    if any(x in q for x in [
        "opportunity",
        "opportunities",
        "growth opportunity"
    ]):
        return "opportunity"

    if any(x in q for x in [
        "growth",
        "growing",
        "increase",
        "increasing",
        "decline",
        "declining"
    ]):
        return "growth"

    if any(x in q for x in [
        "trend",
        "trends"
    ]):
        return "trend"

    return "forecast"


def execute_ml_query(
    engine,
    query: str,
    limit: int = 10
) -> Dict[str, Any]:

    intent = detect_ml_intent(query)

    sql = ML_INTENTS[intent]

    params = {
        "limit": max(1, min(limit, 100))
    }

    with engine.connect() as conn:
        rows = conn.execute(
            text(sql),
            params
        ).mappings().all()

    return {
        "source": "ml_outputs",
        "intent": intent,
        "rows": [dict(row) for row in rows],
        "count": len(rows)
    }
