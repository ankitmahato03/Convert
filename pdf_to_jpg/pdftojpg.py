from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pdf2image import convert_from_bytes
from io import BytesIO
from zipfile import ZipFile
import traceback

app = FastAPI()

# Mount templates directory
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/convert")
async def convert_pdf_to_jpg(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        images = convert_from_bytes(contents, fmt='jpeg')

        if len(images) == 1:
            img_io = BytesIO()
            images[0].save(img_io, format='JPEG')
            img_io.seek(0)
            return StreamingResponse(img_io, media_type="image/jpeg", headers={
                "Content-Disposition": "attachment; filename=converted.jpg"
            })
        else:
            zip_io = BytesIO()
            with ZipFile(zip_io, 'w') as zip_file:
                for i, img in enumerate(images):
                    img_bytes = BytesIO()
                    img.save(img_bytes, format='JPEG')
                    img_bytes.seek(0)
                    zip_file.writestr(f'page_{i+1}.jpg', img_bytes.read())
            zip_io.seek(0)
            return StreamingResponse(zip_io, media_type="application/zip", headers={
                "Content-Disposition": "attachment; filename=converted_images.zip"
            })

    except Exception as e:
        print("Error:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})
