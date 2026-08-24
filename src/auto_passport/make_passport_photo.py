import sys
import io
import os
import cv2
import numpy as np
from PIL import Image
from rembg import remove

def process_passport_photo(input_path, output_jpg_path):
    print(f"Đang xử lý ảnh: {input_path}...")
    
    if not os.path.exists(input_path):
        print(f"Lỗi: Không tìm thấy file {input_path}")
        return

    # 1. Đọc và xoá nền bằng rembg
    with open(input_path, 'rb') as i:
        input_data = i.read()
    
    print("Đang tách nền...")
    subject_data = remove(input_data)
    
    # Chuyển dữ liệu đã xoá nền sang numpy array (OpenCV format) với nền trắng
    subject_pil = Image.open(io.BytesIO(subject_data)).convert("RGBA")
    
    # Tạo nền trắng tạm để phân tích khuôn mặt
    white_bg = Image.new("RGBA", subject_pil.size, (255, 255, 255, 255))
    white_bg.paste(subject_pil, (0, 0), subject_pil)
    white_bg = white_bg.convert("RGB")
    
    # Chuyển qua OpenCV format (BGR)
    img_cv = cv2.cvtColor(np.array(white_bg), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    print("Đang phân tích khuôn mặt và căn chỉnh tỷ lệ chuẩn passport...")
    # 2. Tìm khuôn mặt và mắt
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
    
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    if len(faces) == 0:
        print("Cảnh báo: Không tìm thấy khuôn mặt rõ ràng, dùng thuật toán canh giữa cơ bản.")
        # Fallback cơ bản nếu không thấy mặt
        bbox = subject_pil.getbbox()
        subject_pil = subject_pil.crop(bbox)
        target_subject_height = subject_pil.height
        total_height = int(target_subject_height / 0.75)
        total_width = int(total_height * (4 / 6))
        background = Image.new("RGBA", (total_width, total_height), (255, 255, 255, 255))
        x_offset = (total_width - subject_pil.width) // 2
        y_offset = total_height - subject_pil.height
        background.paste(subject_pil, (x_offset, y_offset), subject_pil)
        final_size = (1200, 1800) # Hệ thống thường yêu cầu pixel lớn (vd 800x1200) thay vì đúng 300 DPI (472x708)
        background = background.resize(final_size, Image.Resampling.LANCZOS)
        final_img_pil = background.convert("RGB")
    else:
        # Xử lý theo quy chuẩn hộ chiếu: 
        # - Diện tích khuôn mặt ~75% ảnh (chiều cao đầu khoảng 75% chiều cao ảnh)
        # - Mắt nằm ở vị trí 2/3 từ dưới lên (tức là 40% từ trên xuống)
        faces = sorted(faces, key=lambda x: x[2]*x[3], reverse=True)
        (x, y, w, h) = faces[0]
        face_roi_gray = gray[y:y+h, x:x+w]
        
        eyes = eye_cascade.detectMultiScale(face_roi_gray)
        if len(eyes) >= 2:
            eyes = sorted(eyes, key=lambda e: e[0]) # xếp theo trục X
            eye1_y = y + eyes[0][1] + eyes[0][3]//2
            eye2_y = y + eyes[-1][1] + eyes[-1][3]//2
            avg_eye_y = (eye1_y + eye2_y) // 2
        elif len(eyes) == 1:
            avg_eye_y = y + eyes[0][1] + eyes[0][3]//2
        else:
            avg_eye_y = int(y + h * 0.4)
            
        head_height = h * 1.4 # Tính toán kích thước cả phần đầu
        
        # Chiều cao tổng theo chuẩn (đầu chiếm khoảng 75%)
        new_height = int(head_height / 0.75)
        new_width = int(new_height * 4 / 6)
        
        target_eye_y = int(new_height * 0.4)
        target_center_x = new_width // 2
        face_center_x = x + w // 2
        
        paste_x = target_center_x - face_center_x
        paste_y = target_eye_y - avg_eye_y
        
        M = np.float32([[1, 0, paste_x], [0, 1, paste_y]])
        shifted = cv2.warpAffine(img_cv, M, (new_width, new_height), borderValue=(255, 255, 255))
        
        final_size = (1200, 1800) # Hệ thống thường yêu cầu pixel lớn (vd 800x1200) thay vì đúng 300 DPI (472x708)
        final_img = cv2.resize(shifted, final_size, interpolation=cv2.INTER_LANCZOS4)
        
        # Convert lại PIL để lưu trữ
        final_img_pil = Image.fromarray(cv2.cvtColor(final_img, cv2.COLOR_BGR2RGB))
    
    # 3. Lưu ảnh đầu ra
    output_jp2_path = output_jpg_path.rsplit('.', 1)[0] + '.jp2'
    
    print(f"Đang lưu file...")
    final_img_pil.save(output_jpg_path, quality=100, dpi=(300, 300))
    print(f"Hoàn thành JPG: {output_jpg_path}")
    
    try:
        final_img_pil.save(output_jp2_path, format="JPEG2000")
        print(f"Hoàn thành JPEG 2000: {output_jp2_path}")
    except Exception as e:
        print(f"Cảnh báo: Không thể lưu JPEG 2000 ({e})")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Cách dùng: python make_passport_photo.py <đường_dẫn_ảnh_gốc> <đường_dẫn_ảnh_kết_quả_jpg>")
        sys.exit(1)
    
    process_passport_photo(sys.argv[1], sys.argv[2])
