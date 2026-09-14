from typing import Dict, Any
from app.business_reasoning import build_business_answer


def build_business_answer_without_llm(
    query: str,
    sql_result=None,
    ml_result=None,
    rag_result=None
) -> Dict[str, Any]:
    return build_business_answer(
        query=query,
        sql_result=sql_result,
        ml_result=ml_result,
        rag_result=rag_result
    )
