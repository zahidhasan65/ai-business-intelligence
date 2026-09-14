from enum import Enum
from typing import List


class QueryRoute(str, Enum):
    SQL = "sql"
    ML = "ml"
    SQL_ML = "sql_ml"
    RAG = "rag"
    SQL_ML_RAG = "sql_ml_rag"


def route_query(query: str) -> QueryRoute:
    q = query.lower().strip()

    # Definition / explanation questions about project metrics
    definition_keywords: List[str] = [
        "what does forecast_vs_3m_pct mean",
        "what is forecast_vs_3m_pct",
        "explain forecast_vs_3m_pct",
        "meaning of forecast_vs_3m_pct",
        "how is forecast_vs_3m_pct calculated",
        "what does forecast vs 3m mean",
        "what is forecast vs 3m"
    ]

    ml_keywords: List[str] = [
        "forecast",
        "predict",
        "prediction",
        "future demand",
        "next month",
        "next month demand",
        "expected demand",
        "will sell",
        "will sales",
        "growth forecast"
    ]

    rag_keywords: List[str] = [
        "return policy",
        "refund policy",
        "shipping policy",
        "payment policy",
        "customer policy",
        "terms",
        "policy",
        "how to return",
        "how can i return"
    ]

    decision_keywords: List[str] = [
        "why",
        "reason",
        "decline",
        "decreased",
        "increased",
        "what should",
        "recommend",
        "recommendation",
        "should we",
        "risk",
        "opportunity",
        "anomaly",
        "problem"
    ]

    if any(keyword in q for keyword in definition_keywords):
        return QueryRoute.RAG

    has_ml = any(keyword in q for keyword in ml_keywords)
    has_rag = any(keyword in q for keyword in rag_keywords)
    has_decision = any(keyword in q for keyword in decision_keywords)

    if has_rag and (has_ml or has_decision):
        return QueryRoute.SQL_ML_RAG

    if has_rag:
        return QueryRoute.RAG

    if has_ml and has_decision:
        return QueryRoute.SQL_ML

    if has_ml:
        return QueryRoute.ML

    if has_decision:
        return QueryRoute.SQL_ML

    return QueryRoute.SQL
