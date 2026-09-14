from typing import Dict, Any

from sqlalchemy import text


SQL_INTENTS = {
    "revenue": """
        SELECT
            COALESCE(SUM(oi.price), 0) AS revenue
        FROM olist_bi.order_items oi
        JOIN olist_bi.orders o
            ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
    """,

    "orders": """
        SELECT
            COUNT(DISTINCT order_id) AS orders
        FROM olist_bi.orders
        WHERE order_status = 'delivered'
    """,

    "products": """
        SELECT
            COUNT(*) AS products
        FROM olist_bi.products
    """,

    "sellers": """
        SELECT
            COUNT(*) AS sellers
        FROM olist_bi.sellers
    """,

    "customers": """
        SELECT
            COUNT(DISTINCT customer_id) AS customers
        FROM olist_bi.orders
        WHERE order_status = 'delivered'
    """,

    "top_products": """
        SELECT
            product_id,
            category,
            orders,
            units_sold,
            revenue,
            average_price
        FROM olist_bi.v_top_products
        ORDER BY revenue DESC
        LIMIT :limit
    """,

    "categories": """
        SELECT
            category,
            orders,
            units_sold,
            revenue,
            average_price
        FROM olist_bi.v_category_performance
        ORDER BY revenue DESC
        LIMIT :limit
    """,

    "monthly_sales": """
        SELECT *
        FROM olist_bi.v_monthly_sales
        ORDER BY month
    """,

    "opportunities": """
        SELECT *
        FROM olist_bi.v_product_opportunities
        ORDER BY opportunity_score DESC
        LIMIT :limit
    """,

    "risks": """
        SELECT *
        FROM olist_bi.v_product_risks
        ORDER BY risk_score DESC
        LIMIT :limit
    """,

    "anomalies": """
        SELECT *
        FROM olist_bi.v_product_anomalies
        ORDER BY anomaly_severity DESC NULLS LAST
        LIMIT :limit
    """
}


def detect_sql_intent(query: str) -> str:
    q = query.lower()

    # Historical movement / decline analysis must use monthly sales.
    if any(x in q for x in [
        "monthly sales",
        "sales by month",
        "monthly revenue",
        "sales trend",
        "revenue trend",
        "sales declined",
        "sales decline",
        "revenue declined",
        "revenue decline",
        "why did sales",
        "why did revenue",
        "why sales",
        "why revenue"
    ]):
        return "monthly_sales"

    if any(x in q for x in ["top product", "best product", "best selling"]):
        return "top_products"

    if any(x in q for x in ["category", "categories"]):
        return "categories"

    if any(x in q for x in ["opportunity", "opportunities"]):
        return "opportunities"

    if any(x in q for x in ["risk", "risks", "risky"]):
        return "risks"

    if any(x in q for x in ["anomaly", "anomalies", "unusual"]):
        return "anomalies"

    if any(x in q for x in ["revenue", "sales", "income"]):
        return "revenue"

    if any(x in q for x in ["order", "orders", "number of orders"]):
        return "orders"

    if any(x in q for x in ["product", "products"]) and any(
        x in q for x in ["how many", "count", "number"]
    ):
        return "products"

    if any(x in q for x in ["seller", "sellers", "vendor", "vendors"]):
        return "sellers"

    if any(x in q for x in ["customer", "customers", "buyer", "buyers"]):
        return "customers"

    return "monthly_sales"


def execute_sql_query(
    engine,
    query: str,
    limit: int = 10
) -> Dict[str, Any]:

    intent = detect_sql_intent(query)

    sql = SQL_INTENTS[intent]

    params = {
        "limit": max(1, min(limit, 100))
    }

    with engine.connect() as conn:
        rows = conn.execute(
            text(sql),
            params
        ).mappings().all()

    return {
        "source": "postgresql",
        "intent": intent,
        "rows": [dict(row) for row in rows],
        "count": len(rows)
    }
