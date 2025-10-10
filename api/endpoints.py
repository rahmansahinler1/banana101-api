from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from .db.database import Database
from .functions.image_functions import ImageFunctions
import logging

# logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
imgf = ImageFunctions()

@router.get("/health")
async def health_check():
    logger.log(msg='Working Fine!', level=1)
    return JSONResponse(
        content={"status": "healthy", "service": "Banana API"},
        status_code=200
    )

@router.post("/get_user")
async def get_user(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")

        with Database() as db:
            user_info = db.get_user_info(user_id)

        return JSONResponse(
            content={
                "user_info": user_info,
            },
            status_code=200,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/get_previews")
async def get_previews(request: Request):
    try:
        # Get payload data
        data = await request.json()
        user_id = data.get("user_id")

        with Database() as db:
            preview_data = db.get_preview_images(user_id)

        return JSONResponse(
            content={
                "previews": preview_data,
            },
            status_code=200,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/get_full_image")
async def get_full_image(request: Request):
    try:
        # Get payload data
        data = await request.json()
        user_id = data.get("user_id")
        image_id = data.get("image_id")

        with Database() as db:
            image_bytes = db.get_full_image(user_id, image_id)

        return JSONResponse(
            content={
                "image_base64": image_bytes,
            },
            status_code=200,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/upload_file")
async def upload_file(request: Request):
    try:
        # Get payload data
        data = await request.json()
        user_id = data.get("user_id")
        category = data.get("category")
        file_bytes = data.get("fileBytes")
        # Get preview bytes
        preview_bytes = imgf.create_preview(file_bytes=file_bytes)

        with Database() as db:
            result = db.upload_file(user_id, category, file_bytes, preview_bytes)

        return JSONResponse(
            content={
                "picture_id": result["picture_id"],
                "preview_base64": result["preview_base64"],
                "created_at": result["created_at"]
            },
            status_code=200,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete_image")
async def delete_image(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        picture_id = data.get("picture_id")

        with Database() as db:
            result = db.delete_picture(user_id, picture_id)

        return JSONResponse(
            content={"success": result},
            status_code=200,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
