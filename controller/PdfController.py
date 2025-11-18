from io import BytesIO

import cv2
import numpy as np
from PIL import Image
from fastapi import APIRouter, UploadFile, Form, Response

from service import convent_page_to_image, pil2cv, mask_text_on_bottom, cv2pil, image_to_base64, pdf_to_pic, pic_to_pdf, \
    bytes_to_base64

app = APIRouter()


@app.post("/convent_pdf_to_image")
async def convent_pdf_to_image(file: UploadFile, merge: str = Form(default="0")):
    """
    替代方案：合并时保持每页原始比例，不填充白色
    """
    res = []    
   
    images = convent_page_to_image(file.file.read(), dpi=200)
    merge = int(merge)
    
    # 处理每页图片
    processed_images = []
    for image_bytes in images:
        cur_img_pil = Image.open(BytesIO(image_bytes))
        cur_img_cv = pil2cv(cur_img_pil)
        
        # 简单的尺寸调整（可选）
        original_height, original_width = cur_img_cv.shape[:2]
        if original_width > 1920:
            scale_factor = 1920 / original_width
            new_width = 1920
            new_height = int(original_height * scale_factor)
            resized_img = cv2.resize(cur_img_cv, (new_width, new_height))
            processed_images.append(resized_img)
        else:
            processed_images.append(cur_img_cv)
    
    if merge == 1:
        # 直接合并，不统一宽度（每页宽度可能不同）
        separator = np.ones((5, max(img.shape[1] for img in processed_images), 3), dtype=np.uint8) * 255
        
        images_with_seps = []
        for i, img in enumerate(processed_images):
            # 如果当前图片宽度小于分隔线宽度，居中显示
            if img.shape[1] < separator.shape[1]:
                padding_left = (separator.shape[1] - img.shape[1]) // 2
                padded_img = np.ones((img.shape[0], separator.shape[1], 3), dtype=np.uint8) * 255
                padded_img[:, padding_left:padding_left+img.shape[1]] = img
                images_with_seps.append(padded_img)
            else:
                images_with_seps.append(img)
            
            if i < len(processed_images) - 1:
                images_with_seps.append(separator)
        
        merge_img = cv2.vconcat(images_with_seps)
        merge_img_pil = cv2pil(merge_img)
        return [image_to_base64(merge_img_pil)]
    else:
        for img in processed_images:
            img_pil = cv2pil(img)
            res.append(image_to_base64(img_pil))
        return res


@app.post("/compress_pdf")
async def compress_pdf(file: UploadFile, size: str = Form(default="10")):
    """
    压缩文件到指定大小
    :param file: 上传的pdf文件
    :param size: 要压缩到的文件大小
    :return: 压缩后文件的base64内容
    """
    file_bites = file.file.read()
    file_size = len(file_bites)
    compress_size = int(size)
    ratio = 80
    ret_pdf_bits = None
    while compress_size * 1024 * 1024 < file_size:
        pics = pdf_to_pic(file_bites, ratio, dpi=300)
        ret_pdf_bits = pic_to_pdf(pics)
        file_size = len(ret_pdf_bits)
        ratio = ratio - 10
        if ratio == 0:
            return Response(status_code=500, content=f"无法压缩到指定size:{size}M", media_type="text/plain")

    if ret_pdf_bits is None:
        return Response(status_code=500, content=f"size:{size}M 的大小必须要小于上传文件的大小:{file_size/1024/1024}M。",
                        media_type="text/plain")
    else:
        return Response(status_code=200, content=bytes_to_base64(ret_pdf_bits), media_type="text/plain")
