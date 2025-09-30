from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from .db.database import Database
import logging

# logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health")
async def health_check():
    logger.log(msg='Working Fine!', level=1)
    return JSONResponse(
        content={"status": "healthy", "service": "Banana API"},
        status_code=200
    )

@router.post("/initialize_user")
async def init(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")

        with Database() as db:
            user_info = db.get_user_info(user_id)
            picture_counts = db.get_picture_counts(user_id)

        return JSONResponse(
            content={
                "user_info": user_info,
                "picture_counts": picture_counts
            },
            status_code=200,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/upload_file")
async def upload_file(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        category = data.get("category")
        file_bytes = data.get("fileBytes")

        with Database() as db:
            result = db.upload_file(user_id, category, file_bytes)

        return JSONResponse(
            content={
                "result": result,
            },
            status_code=200,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    