import cv2
import numpy as np
from PIL import ImageOps, Image
from io import BytesIO
import base64


def pil2cv(image):
    new_image = np.array(image, dtype=np.uint8)
    if new_image.ndim == 2:
        pass
    elif new_image.shape[2] == 3:
        new_image = cv2.cvtColor(new_image, cv2.COLOR_RGB2BGR)
    elif new_image.shape[2] == 4:
        new_image = cv2.cvtColor(new_image, cv2.COLOR_RGBA2BGRA)
    return new_image


def cv2pil(image):
    new_image = image
    if new_image.ndim == 2:
        pass
    elif new_image.shape[2] == 3:
        new_image = cv2.cvtColor(new_image, cv2.COLOR_BGR2RGB)
    elif new_image.shape[2] == 4:
        new_image = cv2.cvtColor(new_image, cv2.COLOR_BGRA2RGBA)
    new_image = Image.fromarray(new_image)
    return new_image


def rotate_image_by_exif(image_pil):
    image_pil = ImageOps.exif_transpose(image_pil)
    return image_pil


# 判别图片中是否存在红色印章（只能判别红色印章）
def check_seal_exit(img):
    img_hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)

    lower_blue = np.array([100, 30, 100])
    upper_blue = np.array([150, 255, 255])

    mask = cv2.inRange(img_hsv, lower_blue, upper_blue)

    res = cv2.bitwise_and(img, img, mask=mask)
    r, g, b = cv2.split(res)
    r_num = 0
    for i in b:
        for j in i:
            if j > 170:
                r_num += 1

    if r_num > 30:
        seal_result = 1  # 该图片有红章
    else:
        seal_result = 0  # 该图片没有红章
    return seal_result


# 红章的提取出来生成图片（只能提取出黑白颜色底的红色印章）
def pick_seal_image(image):
    img_w = 768 if image.shape[1] > 768 else image.shape[1]
    image = cv2.resize(image, (img_w, int(img_w * image.shape[0] / image.shape[1])),
                       interpolation=cv2.INTER_AREA if img_w > 1024 else cv2.INTER_CUBIC)
    img_png = cv2.cvtColor(image, cv2.COLOR_RGB2RGBA)
    hue_image = cv2.cvtColor(img_png, cv2.COLOR_BGR2HSV)

    img_real = None
    mask_ranges = [[np.array([0, 43, 46]), np.array([10, 255, 255])]
        , [np.array([156, 43, 46]), np.array([180, 255, 255])]]
    for img_range in mask_ranges:
        th = cv2.inRange(hue_image, img_range[0], img_range[1])
        element = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        th = cv2.dilate(th, element)
        index1 = th == 255
        mask = np.zeros(img_png.shape, np.uint8)
        mask[:, :, :] = (255, 255, 255, 0)
        mask[index1] = img_png[index1]
        if img_real is None:
            img_real = mask
        else:
            img_real = cv2.add(img_real, mask)

    white_px = np.asarray([255, 255, 255, 255])
    (row, col, _) = img_real.shape
    for r in range(row):
        for c in range(col):
            px = img_real[r][c]
            if all(px == white_px):
                img_real[r][c] = img_png[r][c]

    # 扩充图片防止截取部分
    img4png = cv2.copyMakeBorder(img_real, 50, 50, 50, 50, cv2.BORDER_CONSTANT, value=[255, 255, 255, 0])
    img5png = cv2.copyMakeBorder(image, 50, 50, 50, 50, cv2.BORDER_CONSTANT, value=[255, 255, 255, 0])
    img2gray = cv2.cvtColor(img4png, cv2.COLOR_RGBA2GRAY)
    retval, gray_first = cv2.threshold(img2gray, 253, 255, cv2.THRESH_BINARY_INV)

    # 形态学去噪，cv2.MORPH_OPEN先腐蚀再膨胀，cv2.MORPH_CLOSE先膨胀再腐蚀
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    img_real = cv2.morphologyEx(gray_first, cv2.MORPH_OPEN, kernel, iterations=1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (100, 100))
    img_real = cv2.morphologyEx(img_real, cv2.MORPH_CLOSE, kernel, iterations=1)

    c_canny_img = cv2.Canny(img_real, 10, 10)

    contours, hierarchy = cv2.findContours(c_canny_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    areas = []
    for i, cnt in enumerate(contours):
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        ars = [area, i]
        areas.append(ars)
    areas = sorted(areas, reverse=True)
    print(areas)
    stamps = []
    for item in areas[:4]:
        max_ares = item
        x, y, w, h = cv2.boundingRect(contours[max_ares[1]])
        temp = img5png[y:(y + h), x:(x + w)]
        if temp.shape[0] < temp.shape[1]:
            zh = int((temp.shape[1] - temp.shape[0]) / 2)
            temp = cv2.copyMakeBorder(temp, zh, zh, 0, 0, cv2.BORDER_CONSTANT, value=[255, 255, 255, 0])
        else:
            zh = int((temp.shape[0] - temp.shape[1]) / 2)
            temp = cv2.copyMakeBorder(temp, 0, 0, zh, zh, cv2.BORDER_CONSTANT, value=[255, 255, 255, 0])
        dst = cv2.resize(temp, (300, 300), interpolation=cv2.INTER_AREA if x > 300 or y > 300 else cv2.INTER_CUBIC)
        stamps.append(dst)
    all_stamp = cv2.hconcat(stamps)
    return all_stamp


def image_to_base64(image: Image.Image, fmt='png') -> str:
    output_buffer = BytesIO()
    image.save(output_buffer, format=fmt)
    byte_data = output_buffer.getvalue()
    base64_str = base64.b64encode(byte_data).decode('utf-8')
    return base64_str