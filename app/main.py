from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.recommender.engine import recommend_pc
from app.recommender.direct_engine import recommend_pc_direct
from app.schemas import UserInput

app = FastAPI(title="PC Recommendation System")

# 🔓 Allow frontend (keep open for now)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # IMPORTANT for Railway + sample frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Root endpoint (Railway / browser check)
@app.get("/")
def root():
    return {"status": "Backend running 🚀"}

# 🔥 Direct recommendation endpoint
@app.post("/recommend_direct")
def recommend_direct(user_input: UserInput):
    return recommend_pc_direct(user_input)
