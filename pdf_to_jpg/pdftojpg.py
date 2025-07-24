from flask import Flask, request, send_file, render_template
from pdf2image import convert_from_bytes
from io import BytesIO
from zipfile import ZipFile

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_pdf_to_jpg():
    try:
        file = request.files['file']
        images = convert_from_bytes(file.read(), fmt='jpeg')

        if len(images) == 1:
            img_io = BytesIO()
            images[0].save(img_io, format='JPEG')
            img_io.seek(0)
            return send_file(img_io, mimetype='image/jpeg', download_name='converted.jpg')
        else:
            zip_io = BytesIO()
            with ZipFile(zip_io, 'w') as zip_file:
                for i, img in enumerate(images):
                    img_bytes = BytesIO()
                    img.save(img_bytes, format='JPEG')
                    img_bytes.seek(0)
                    zip_file.writestr(f'page_{i+1}.jpg', img_bytes.read())
            zip_io.seek(0)
            return send_file(zip_io, mimetype='application/zip', download_name='converted_images.zip')

    except Exception as e:
        import traceback
        print("Error:", traceback.format_exc())
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True)
