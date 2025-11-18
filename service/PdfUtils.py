from typing import List

import cv2
import fitz
import numpy as np


def convent_page_to_image(pdf_bits, dpi=200) -> List:
    pdf_page_img_data = []
    pdf_doc = fitz.open("pdf", pdf_bits)
    pages = pdf_doc.pages()

    for page in pages:
        # 使用DPI而不是固定的缩放因子
        # DPI 300 是高质量打印标准，DPI 150 是标准屏幕质量
        zoom_x = dpi / 72  # PDF默认DPI是72
        zoom_y = dpi / 72
        mat = fitz.Matrix(zoom_x, zoom_y)
        pix = page.get_pixmap(matrix=mat, dpi=dpi, colorspace='rgb', alpha=False)
        img_bits = pix.tobytes()
        pdf_page_img_data.append(img_bits)
    return pdf_page_img_data


def pic_to_pdf(images):
    doc = fitz.open()
    for img in images:
        img_doc = fitz.open("jpg", img)
        pdf_bytes = img_doc.convert_to_pdf()
        img_pdf = fitz.open("pdf", pdf_bytes)
        doc.insert_pdf(img_pdf)

    return doc.write()


def pdf_to_pic(pdf, ratio=50, dpi=300):
    """
    将PDF转换为高质量图片

    :param pdf: pdf文件（bytes）
    :param ratio:图片压缩比例
    :param dpi: 图片DPI，默认300
    :return:
    """
    doc = fitz.open("pdf", pdf)
    fitz.paper_size("a4")
    pages_count = doc.page_count
    pic_list = []

    for pg in range(pages_count):
        page = doc[pg]
        zoom_x = dpi / 72  # PDF默认DPI是72
        zoom_y = dpi / 72
        mat = fitz.Matrix(zoom_x, zoom_y)
        pm = page.get_pixmap(matrix=mat, dpi=dpi, colorspace='rgb', alpha=False)
        img_bits = pm.tobytes()
        np_array = np.frombuffer(img_bits, np.uint8)
        image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        params = [cv2.IMWRITE_JPEG_QUALITY, ratio]  # ratio:0~100
        image = cv2.imencode(".jpg", image, params)[1]
        image = (np.array(image)).tobytes()
        pic_list.append(image)
    return pic_list
