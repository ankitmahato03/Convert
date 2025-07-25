from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF
from typing import List
from PIL import Image
from io import BytesIO
from zipfile import ZipFile
import traceback

#from here
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
#to here

@app.post("/pdf_to_jpg")
async def convert_pdf_to_jpg(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        images = Image.open(BytesIO(contents)).convert("RGB")._getexif()
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

@app.post("/jpg-to-pdf")
async def convert_images_to_pdf(files: List[UploadFile] = File(...)):
    try:
        images = []
        for file in files:
            contents = await file.read()
            img = Image.open(BytesIO(contents)).convert("RGB")
            images.append(img)

        if not images:
            return JSONResponse(status_code=400, content={"error": "No valid images provided"})

        pdf_io = BytesIO()
        images[0].save(pdf_io, format='PDF', save_all=True, append_images=images[1:])
        pdf_io.seek(0)

        return StreamingResponse(pdf_io, media_type="application/pdf", headers={
            "Content-Disposition": "attachment; filename=converted.pdf"
        })

    except Exception as e:
        print("Error:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/lock-pdf")
async def lock_pdf(file: UploadFile = File(...), password: str = "secure123"):
    try:
        contents = await file.read()

        reader = PdfReader(BytesIO(contents))
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        writer.encrypt(password)

        output_io = BytesIO()
        writer.write(output_io)
        output_io.seek(0)

        return StreamingResponse(output_io, media_type="application/pdf", headers={
            "Content-Disposition": "attachment; filename=locked.pdf"
        })

    except Exception as e:
        print("Error:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/unlock-pdf")
async def unlock_pdf(file: UploadFile = File(...), password: str = File(...)):
    try:
        contents = await file.read()
        input_io = BytesIO(contents)

        reader = PdfReader(input_io)

        if reader.is_encrypted:
            if not reader.decrypt(password):
                return JSONResponse(status_code=403, content={"error": "Incorrect password or decryption failed"})

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        output_io = BytesIO()
        writer.write(output_io)
        output_io.seek(0)

        return StreamingResponse(output_io, media_type="application/pdf", headers={
            "Content-Disposition": "attachment; filename=unlocked.pdf"
        })

    except Exception as e:
        print("Error:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/compress-pdf")
async def compress_pdf(file: UploadFile = File(...), compression_ratio: int = 50):
    """
    Compresses a PDF by reducing image quality to the given percentage.
    """
    try:
        if not (1 <= compression_ratio <= 100):
            return JSONResponse(status_code=400, content={"error": "Compression ratio must be between 1 and 100"})

        contents = await file.read()
        pdf_in = fitz.open(stream=contents, filetype="pdf")

        for page_index in range(len(pdf_in)):
            images = pdf_in.get_page_images(page_index)
            for img in images:
                xref = img[0]
                base_image = pdf_in.extract_image(xref)
                image_bytes = base_image["image"]
                img_ext = base_image["ext"]

                # Only compress JPEG or PNG images
                if img_ext.lower() not in ["jpeg", "jpg", "png"]:
                    continue

                image = Image.open(BytesIO(image_bytes)).convert("RGB")
                img_io = BytesIO()
                image.save(img_io, format="JPEG", quality=compression_ratio)
                img_io.seek(0)

                # Replace the image stream in the PDF
                pdf_in.update_stream(xref, img_io.read())

        out_stream = BytesIO()
        pdf_in.save(out_stream)
        out_stream.seek(0)

        return StreamingResponse(out_stream, media_type="application/pdf", headers={
            "Content-Disposition": "attachment; filename=compressed.pdf"
        })

    except Exception as e:
        print("Error:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})

    """
    Compresses a PDF by reducing image quality to the given percentage.
    Example: compression_ratio=50 means reduce image quality to 50%.
    """
    try:
        if not (1 <= compression_ratio <= 100):
            return JSONResponse(status_code=400, content={"error": "Compression ratio must be between 1 and 100"})

        contents = await file.read()
        pdf_in = fitz.open(stream=contents, filetype="pdf")

        pdf_out = fitz.open()
        for page in pdf_in:
            single_page = pdf_out.new_page(width=page.rect.width, height=page.rect.height)
            single_page.show_pdf_page(page.rect, pdf_in, page.number)

        for i in range(len(pdf_out)):
            images = pdf_out[i].get_images(full=True)
            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = pdf_out.extract_image(xref)
                image_bytes = base_image["image"]
                img_ext = base_image["ext"]

                image = Image.open(BytesIO(image_bytes))
                img_io = BytesIO()
                image.save(img_io, format="JPEG", quality=compression_ratio)
                img_io.seek(0)
                pdf_out.update_image(xref, img_io.read())

        out_stream = BytesIO()
        pdf_out.save(out_stream)
        out_stream.seek(0)

        return StreamingResponse(out_stream, media_type="application/pdf", headers={
            "Content-Disposition": "attachment; filename=compressed.pdf"
        })

    except Exception as e:
        print("Error:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})