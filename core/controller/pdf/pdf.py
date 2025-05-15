from http import HTTPStatus
from flask import Flask, request, jsonify, Blueprint
import base64
from io import BytesIO
import pdfplumber
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.utils import ImageReader
from PIL import Image
import hashlib
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PDF = Blueprint('PDF', __name__)

app = Flask(__name__)

@PDF.route('/generateMercadoLibrePDF', methods=['POST'])
def generate_mercadolibre_pdf():
    try:
        data = request.get_json()

        if not data or 'LIST_PDFS' not in data:
            return jsonify({"ERROR": "MISSING 'LIST[] PDF'"}), HTTPStatus.BAD_REQUEST

        pdf_list_base64 = data['LIST_PDFS'][0]

        crop_coords = (32, 30, 287, 559)
        custom_scale_factor = 2.172
        page_width, page_height = landscape(A4)
        margin = 28
        max_img_width = 150
        max_img_height = 150
        max_crops_per_page = 5

        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=(page_width, page_height))

        x_offset = margin
        y_offset = page_height - margin - max_img_height
        crops_per_page = 0
        added_pdfs = set()

        for _, pdf_b64 in enumerate(pdf_list_base64):
            pdf_bytes = base64.b64decode(pdf_b64)
            pdf_hash = hashlib.md5(pdf_bytes).hexdigest()

            if pdf_hash in added_pdfs:
                continue

            with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                page = pdf.pages[0]

                page_w = page.width
                page_h = page.height

                x0 = max(0, min(crop_coords[0], page_w))
                y0 = max(0, min(crop_coords[1], page_h))
                x1 = max(0, min(crop_coords[2], page_w))
                y1 = max(0, min(crop_coords[3], page_h))

                if x1 > x0 and y1 > y0:
                    cropped = page.crop((x0, y0, x1, y1))
                    img = cropped.to_image(resolution=500)

                    img_byte_arr = BytesIO()
                    img.save(img_byte_arr, format="PNG")
                    img_byte_arr.seek(0)

                    image_reader = ImageReader(img_byte_arr)

                    with Image.open(img_byte_arr) as im:
                        img_w, img_h = im.size

                        scale_w = (max_img_width / img_w) * custom_scale_factor
                        scale_h = (max_img_height / img_h) * custom_scale_factor
                        scale = min(scale_w, scale_h, 1)

                        draw_w = img_w * scale
                        draw_h = img_h * scale

                        c.drawImage(image_reader, x_offset, y_offset + (max_img_height - draw_h),
                                    width=draw_w, height=draw_h)

                        x_offset += draw_w
                        crops_per_page += 1

                        if crops_per_page >= max_crops_per_page:
                            c.showPage()
                            x_offset = margin
                            y_offset = page_height - margin - max_img_height
                            crops_per_page = 0

                    added_pdfs.add(pdf_hash)

        c.save()

        pdf_buffer.seek(0)
        pdf_base64 = base64.b64encode(pdf_buffer.read()).decode('utf-8')
        pdf_buffer.close()

        return jsonify({'BASE64PDF': pdf_base64}), 200

    except Exception as e:
        return jsonify({"ERROR": "ORDER NOT FOUND"}), HTTPStatus.NOT_FOUND
