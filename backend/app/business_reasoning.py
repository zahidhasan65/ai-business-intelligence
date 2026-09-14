from typing import Dict, Any, List


def _num(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _pct(value):
    return f"{_num(value):.1f}%"


def analyze_sql(sql_result) -> Dict[str, Any]:
    if not sql_result or not sql_result.get("rows"):
        return {}

    intent = sql_result.get("intent")
    rows = sql_result["rows"]

    if intent == "revenue":
        revenue = _num(rows[0].get("revenue"))
        return {
            "summary": f"Delivered-order product revenue is {revenue:,.2f}.",
            "insights": [
                f"Total delivered-order product revenue: {revenue:,.2f}."
            ],
            "recommendations": [
                "Use this figure as the baseline for revenue performance analysis."
            ]
        }

    if intent == "orders":
        orders = int(_num(rows[0].get("orders")))
        return {
            "summary": f"There are {orders:,} delivered orders in the dataset.",
            "insights": [
                f"Delivered order volume is {orders:,}."
            ],
            "recommendations": [
                "Use delivered orders as the operational baseline for business analysis."
            ]
        }

    if intent == "products":
        products = int(_num(rows[0].get("products")))
        return {
            "summary": f"The dataset contains {products:,} products.",
            "insights": [
                f"Product catalog size: {products:,}."
            ],
            "recommendations": [
                "Use product-level intelligence to prioritize high-value products."
            ]
        }

    if intent == "sellers":
        sellers = int(_num(rows[0].get("sellers")))
        return {
            "summary": f"The dataset contains {sellers:,} sellers.",
            "insights": [
                f"Seller base: {sellers:,}."
            ],
            "recommendations": [
                "Compare seller performance before making supplier-level decisions."
            ]
        }

    if intent == "customers":
        customers = int(_num(rows[0].get("customers")))
        return {
            "summary": f"There are {customers:,} customers associated with delivered orders.",
            "insights": [
                f"Delivered-order customer count: {customers:,}."
            ],
            "recommendations": [
                "Combine customer and product behavior for deeper segmentation later."
            ]
        }

    if intent == "top_products":
        top = rows[:5]
        insights = []
        for i, row in enumerate(top, 1):
            insights.append(
                f"{i}. {row.get('category', 'unknown')} "
                f"generated { _num(row.get('revenue')):,.2f} revenue "
                f"from {int(_num(row.get('units_sold'))):,} units."
            )

        return {
            "summary": "The leading products are concentrated among the highest-revenue product records.",
            "insights": insights,
            "recommendations": [
                "Protect availability of the highest-revenue products.",
                "Investigate whether top products can support cross-selling or promotion."
            ]
        }

    if intent == "categories":
        top = rows[:5]
        insights = []
        for i, row in enumerate(top, 1):
            insights.append(
                f"{i}. {row.get('category', 'unknown')}: "
                f"{_num(row.get('revenue')):,.2f} revenue "
                f"across {int(_num(row.get('orders'))):,} orders."
            )

        return {
            "summary": "The category ranking shows where the largest revenue contribution comes from.",
            "insights": insights,
            "recommendations": [
                "Prioritize high-revenue categories for inventory and commercial planning.",
                "Compare category growth before increasing investment."
            ]
        }

    if intent == "opportunities":
        top = rows[:5]
        insights = []
        recommendations = []

        for i, row in enumerate(top, 1):
            category = row.get("category", "unknown")
            score = _num(row.get("opportunity_score"))
            health = _num(row.get("health_score"))
            risk = _num(row.get("risk_score"))
            priority = row.get("decision_priority", "unknown")

            insights.append(
                f"{i}. {category}: opportunity score {score:.1f}, "
                f"health score {health:.1f}, risk score {risk:.1f}, "
                f"priority {priority}."
            )

            if risk < 15 and health >= 75:
                recommendations.append(
                    f"Prioritize {category} products because opportunity is strong "
                    f"while health and risk signals remain favorable."
                )
            elif score >= 70:
                recommendations.append(
                    f"Investigate {category} products for additional sales or inventory opportunities."
                )

        return {
            "summary": f"Identified {len(rows)} leading opportunity records, with the highest-scoring products shown first.",
            "insights": insights,
            "recommendations": recommendations[:5]
        }

    if intent == "risks":
        top = rows[:5]
        insights = []
        recommendations = []

        for i, row in enumerate(top, 1):
            category = row.get("category", "unknown")
            score = _num(row.get("risk_score"))
            health = _num(row.get("health_score"))
            status = row.get("health_status", "unknown")
            priority = row.get("decision_priority", "unknown")

            insights.append(
                f"{i}. {category}: risk score {score:.1f}, "
                f"health score {health:.1f}, status {status}, "
                f"priority {priority}."
            )

            if status in ("critical", "at_risk") or score >= 70:
                recommendations.append(
                    f"Investigate {category} products immediately and review demand, "
                    f"inventory, and commercial performance."
                )
            else:
                recommendations.append(
                    f"Monitor {category} products for further deterioration."
                )

        return {
            "summary": "The risk ranking highlights products requiring monitoring or intervention.",
            "insights": insights,
            "recommendations": recommendations[:5]
        }

    if intent == "anomalies":
        top = rows[:5]
        insights = []
        recommendations = []

        for i, row in enumerate(top, 1):
            category = row.get("category", "unknown")
            severity = _num(row.get("anomaly_severity"))
            actual = _num(row.get("actual_demand"))
            expected = _num(row.get("expected_demand"))
            anomaly_type = row.get("anomaly_type", "unknown")

            insights.append(
                f"{i}. {category}: {anomaly_type} anomaly, "
                f"severity {severity:.1f}, actual demand {actual:.1f} "
                f"vs expected {expected:.1f}."
            )

            recommendations.append(
                f"Investigate the demand deviation for {category} before making inventory decisions."
            )

        return {
            "summary": "The system detected unusual demand behavior among the returned products.",
            "insights": insights,
            "recommendations": recommendations[:5]
        }

    if intent == "monthly_sales":
        if not rows:
            return {}

        # Detect a sparse terminal month. With delivered-order analysis,
        # the final purchase month can be incomplete because many orders
        # may not yet have reached delivered status.
        analysis_rows = list(rows)

        while len(analysis_rows) >= 2:
            current = analysis_rows[-1]
            previous_candidate = analysis_rows[-2]

            current_orders = _num(current.get("orders"))
            previous_orders = _num(previous_candidate.get("orders"))

            if previous_orders > 0 and current_orders < (previous_orders * 0.10):
                analysis_rows.pop()
            else:
                break

        latest = analysis_rows[-1]
        previous = analysis_rows[-2] if len(analysis_rows) >= 2 else None

        latest_revenue = _num(
            latest.get("revenue", latest.get("sales", latest.get("total_revenue")))
        )

        insights = [
            f"Latest reliable monthly revenue: {latest_revenue:,.2f}."
        ]

        recommendations = [
            "Review monthly sales trend together with product-level forecasts before planning inventory."
        ]

        # Explain why the terminal month was excluded when applicable.
        if len(analysis_rows) < len(rows):
            excluded_month = rows[-1].get("month", "latest month")
            insights.append(
                f"The terminal month ({excluded_month}) was excluded from decline analysis "
                "because its delivered-order volume was unusually low relative to the previous month."
            )

        if previous:
            previous_revenue = _num(
                previous.get("revenue", previous.get("sales", previous.get("total_revenue")))
            )

            if previous_revenue:
                change = ((latest_revenue - previous_revenue) / previous_revenue) * 100
                direction = "increased" if change >= 0 else "decreased"
                insights.append(
                    f"Revenue {direction} by {abs(change):.1f}% compared with the previous reliable month."
                )

        return {
            "summary": "Monthly sales history was analyzed to identify recent movement.",
            "insights": insights,
            "recommendations": recommendations
        }

    return {
        "summary": "SQL evidence was retrieved successfully.",
        "insights": [],
        "recommendations": []
    }


def analyze_ml(ml_result) -> Dict[str, Any]:
    if not ml_result or not ml_result.get("rows"):
        return {}

    intent = ml_result.get("intent")
    rows = ml_result["rows"]

    # Technical metric definition questions should return an explanation,
    # not a product ranking.
    query_text = str(ml_result.get("query", "")).lower()

    if "forecast_vs_3m_pct" in query_text:
        return {
            "summary": (
                "forecast_vs_3m_pct measures how much the forecasted product "
                "demand differs from the recent 3-month demand baseline."
            ),
            "insights": [
                "A positive percentage means forecast demand is above the recent 3-month baseline.",
                "A negative percentage means forecast demand is below the recent 3-month baseline.",
                "For example, +29.8% means forecast demand is approximately 29.8% higher than the recent 3-month baseline."
            ],
            "recommendations": [
                "Use this metric as a relative demand-change signal alongside forecast demand and product volume.",
                "Validate very large percentages when the recent baseline is very low."
            ]
        }

    # Technical metric definition questions should return an explanation,
    # not a product ranking.
    query_text = str(ml_result.get("query", "")).lower()

    if "forecast_vs_3m_pct" in query_text:
        return {
            "summary": (
                "forecast_vs_3m_pct measures how much the forecasted product "
                "demand differs from the recent 3-month demand baseline."
            ),
            "insights": [
                "A positive percentage means forecast demand is above the recent 3-month baseline.",
                "A negative percentage means forecast demand is below the recent 3-month baseline.",
                "For example, +29.8% means forecast demand is approximately 29.8% higher than the recent 3-month baseline."
            ],
            "recommendations": [
                "Use this metric as a relative demand-change signal alongside forecast demand and product volume.",
                "Validate very large percentages when the recent baseline is very low."
            ]
        }

    if intent in ("forecast", "growth"):
        top = rows[:5]
        insights = []

        for i, row in enumerate(top, 1):
            category = row.get("category", "unknown")
            demand = _num(row.get("forecast_demand"))
            growth = row.get("forecast_vs_3m_pct")

            growth_text = "N/A" if growth is None else _pct(growth)

            insights.append(
                f"{i}. {category}: forecast demand {demand:.2f}, "
                f"forecast vs recent 3-month baseline {growth_text}."
            )

        return {
            "summary": "The demand model provides product-level forward demand estimates.",
            "insights": insights,
            "recommendations": [
                "Use high-demand forecasts as inventory-planning signals rather than guaranteed sales.",
                "Validate very large percentage changes when recent demand is low."
            ]
        }

    if intent == "trend":
        top = rows[:5]
        insights = []

        for i, row in enumerate(top, 1):
            category = row.get("category", "unknown")
            trend = row.get("trend", "unknown")
            strength = _num(row.get("trend_strength"))
            change = row.get("forecast_vs_3m_pct")

            insights.append(
                f"{i}. {category}: trend {trend}, strength {strength:.2f}, "
                f"forecast-vs-baseline {('N/A' if change is None else _pct(change))}."
            )

        return {
            "summary": "Product trends were evaluated using the project's calibrated trend signals.",
            "insights": insights,
            "recommendations": [
                "Prioritize persistent positive trends for growth experiments.",
                "Investigate persistent negative trends before increasing inventory."
            ]
        }

    if intent == "opportunity":
        return analyze_sql({
            "intent": "opportunities",
            "rows": rows
        })

    if intent == "risk":
        return analyze_sql({
            "intent": "risks",
            "rows": rows
        })

    if intent == "anomaly":
        return analyze_sql({
            "intent": "anomalies",
            "rows": rows
        })

    return {}


def build_business_answer(
    query: str,
    sql_result=None,
    ml_result=None,
    rag_result=None
) -> Dict[str, Any]:

    # Handle technical metric definition questions directly from the
    # project knowledge base semantics.
    query_lower = query.lower()

    if "forecast_vs_3m_pct" in query_lower:
        return {
            "query": query,
            "answer": (
                "forecast_vs_3m_pct is the percentage difference between "
                "forecast demand and recent 3-month demand. Positive values "
                "indicate expected growth relative to the recent 3-month "
                "baseline, while negative values indicate expected decline."
            ),
            "insights": [
                "Positive forecast_vs_3m_pct means forecast demand is above the recent 3-month baseline.",
                "Negative forecast_vs_3m_pct means forecast demand is below the recent 3-month baseline.",
                "For example, +29.8% means forecast demand is approximately 29.8% above the recent 3-month baseline."
            ],
            "recommendations": [
                "Use this metric as a relative demand-change signal alongside forecast demand and product volume.",
                "Validate very large percentage changes when the recent baseline is very low."
            ],
            "sources": ["Project knowledge base"],
            "limitations": [
                "Forecasts are model estimates, not guaranteed future sales.",
                "Very low-volume products can produce large percentage changes from small baselines."
            ],
            "evidence": {
                "sql": sql_result,
                "ml": ml_result,
                "rag": rag_result
            },
            "engine": {
                "type": "deterministic_business_reasoning",
                "external_llm_api": False
            }
        }

    sql_analysis = analyze_sql(sql_result)
    ml_analysis = analyze_ml(ml_result)

    insights: List[str] = []
    recommendations: List[str] = []
    sources: List[str] = []

    if sql_result and sql_result.get("rows"):
        sources.append("PostgreSQL SQL analytics")
        insights.extend(sql_analysis.get("insights", []))
        recommendations.extend(sql_analysis.get("recommendations", []))

    if ml_result and ml_result.get("rows"):
        sources.append("ML intelligence outputs")
        insights.extend(ml_analysis.get("insights", []))
        recommendations.extend(ml_analysis.get("recommendations", []))

    rag_used = bool(rag_result and rag_result.get("context"))

    if rag_used:
        sources.append("Project knowledge base")

    if not insights:
        insights.append(
            "No structured business evidence was available for this query."
        )

    # Remove duplicate recommendations while preserving order.
    recommendations = list(dict.fromkeys(recommendations))[:6]

    # Build a deterministic business explanation.
    summaries = [
        sql_analysis.get("summary"),
        ml_analysis.get("summary")
    ]
    summaries = [x for x in summaries if x]

    if summaries:
        answer = " ".join(summaries)
    else:
        answer = (
            "I could not generate a business conclusion from the available "
            "structured evidence."
        )

    limitations = [
        "Recommendations are based on the project's analytical signals and are not guaranteed business outcomes.",
        "Very low-volume products can produce large percentage changes from small baselines."
    ]

    if rag_result and "Limitations" in rag_result.get("context", ""):
        limitations.append(
            "The project knowledge base notes that forecasts are model estimates rather than guaranteed future sales."
        )

    return {
        "query": query,
        "answer": answer,
        "insights": insights[:10],
        "recommendations": recommendations,
        "sources": sources,
        "limitations": list(dict.fromkeys(limitations)),
        "evidence": {
            "sql": sql_result,
            "ml": ml_result,
            "rag": rag_result
        },
        "engine": {
            "type": "deterministic_business_reasoning",
            "external_llm_api": False
        }
    }




