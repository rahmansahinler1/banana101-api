from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Logging
import logging
error_handler = logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'errors.log'))
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

logging.basicConfig(
    level=logging.ERROR,
    handlers=[error_handler]
)

# API
from .endpoints import router
app = FastAPI(title="Unmarble API", version="1.0.0")

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

app.include_router(router, prefix="/v1")

@app.get("/")
async def root():
    return {"message": "unmarble API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)