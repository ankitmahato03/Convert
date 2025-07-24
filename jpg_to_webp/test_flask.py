from flask import Flask, request, send_file, render_template
from PIL import Image
from io import BytesIO
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_jpg_to_webp():
    if 'file' not in request.files:
        return {'error': 'No file part in the request'}, 400

    file = request.files['file']
    if file.filename == '':
        return {'error': 'No selected file'}, 400

    quality = request.form.get('quality', default=80, type=int)

    try:
        img = Image.open(file.stream).convert('RGB')
        webp_io = BytesIO()
        img.save(webp_io, format='WEBP', quality=quality)
        webp_io.seek(0)

        return send_file(webp_io, mimetype='image/webp')
    except Exception as e:
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True)