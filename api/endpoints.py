from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from .db.database import Database
from .functions.image_functions import ImageFunctions
import logging
import base64

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
            preview_image_data = db.get_preview_images(user_id)
            preview_generation_data = db.get_preview_generations(user_id)

        return JSONResponse(
            content={
                "image_previews": preview_image_data,
                "generation_previews": preview_generation_data
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
            image_bytes = db.get_full_image(
                user_id,
                image_id
                )
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        return JSONResponse(
            content={
                "image_base64": image_base64,
            },
            status_code=200,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/upload_image")
async def upload_image(request: Request):
    try:
        # Get payload data
        data = await request.json()
        user_id = data.get("user_id")
        category = data.get("category")
        image_bytes = data.get("imageBytes")
        # Get preview bytes
        decoded_bytes = base64.b64decode(image_bytes)
        preview_bytes = imgf.create_preview(image_bytes=decoded_bytes)

        with Database() as db:
            result = db.insert_image(
                user_id,
                category,
                decoded_bytes,
                preview_bytes
                )

        return JSONResponse(
            content={
                "image_id": result["image_id"],
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
        image_id = data.get("image_id")

        with Database() as db:
            result = db.delete_image(
                user_id,
                image_id
                )

        return JSONResponse(
            content={"success": result},
            status_code=200,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete_generated_image")
async def delete_generated_image(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        image_id = data.get("image_id")

        with Database() as db:
            result = db.delete_generated_image(
                user_id,
                image_id
                )

        return JSONResponse(
            content={"success": result},
            status_code=200,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/generate_image")
async def generate_image(request: Request):
    try:
        # Get payload data
        data = await request.json()
        user_id = data.get("user_id")
        yourself_image_id = data.get("yourself_image_id")
        clothing_image_id = data.get("clothing_image_id")

        # Get image data
        with Database() as db:
            yourself_image_bytes = db.get_image(
                user_id,
                yourself_image_id
                )
            clothing_image_bytes = db.get_image(
                user_id,
                clothing_image_id
                )
        
        # Generate image
        generated_image_bytes = imgf.generate_image(
            yourself_image_bytes,
            clothing_image_bytes
            )
        image_base64 = base64.b64encode(generated_image_bytes).decode('utf-8')

        # Save generation to the db
        generated_preview_bytes = imgf.create_preview(generated_image_bytes)
        with Database() as db:
            result = db.insert_generated_image(
                user_id,
                yourself_image_id,
                clothing_image_id,
                generated_image_bytes,
                generated_preview_bytes
                )

        return JSONResponse(
            content={
                "image_id": result["image_id"],
                "image_base64": image_base64,
                "preview_base64": result["preview_base64"],
                "created_at": result["created_at"]
            },
            status_code=200,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
