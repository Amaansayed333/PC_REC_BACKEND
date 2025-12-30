from app.recommender.direct_llm import get_direct_recommendations


def recommend_pc_direct(user_input):
    user_dict = user_input.dict() if hasattr(user_input, "dict") else user_input
    recommendations = get_direct_recommendations(user_dict)

    if isinstance(recommendations, dict) and recommendations.get("error"):
        return {"recommendations": [recommendations]}

    if isinstance(recommendations, list):
        cleaned = [r for r in recommendations if isinstance(r, dict)]
        return {"recommendations": cleaned[:3]}

    return {"recommendations": [{"error": "invalid_llm_response", "raw": recommendations}]}
