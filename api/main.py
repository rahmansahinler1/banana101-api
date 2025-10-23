from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .endpoints import router

app = FastAPI(title="Unmarble API", version="1.0.0")

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:5174",
        "https://www.unmarble.com",
        "https://unmarble.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router, prefix="/v1")

# Initial loading
@app.get("/")
async def root():
    return {"message": "unmarble API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)