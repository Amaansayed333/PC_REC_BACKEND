from app.recommender.llm import get_pc_recommendations
from app.recommender.normalizer import normalize_user_input


def recommend_pc(user_input):
    user_dict = user_input.dict()
    clean_input = normalize_user_input(user_dict)

    recommendations = get_pc_recommendations(clean_input)

    if isinstance(recommendations, dict):
        return {"recommendations": [recommendations]}

    return {"recommendations": recommendations[:3]}
