# Tài liệu: Ánh xạ Tiêu chuẩn Hộ chiếu Việt Nam vào Thuật toán

Tài liệu này giải thích chi tiết cách hệ thống `make_passport_photo.py` áp dụng tự động các tiêu chuẩn của Bộ Công an/Cổng dịch vụ công Quốc gia vào mã nguồn xử lý ảnh.

## 1. Tỉ lệ 4x6 & Chuẩn pixel độ lớn phương ngang
**Yêu cầu:** Tỉ lệ ảnh 4x6, độ lớn phương ngang đủ lớn để vượt qua kiểm duyệt.
**Thực thi trong Code:**
Hệ thống sử dụng kích thước tĩnh `1200x1800` pixel. Kích thước này tỷ lệ chuẩn 2:3 (tương đương 4x6 cm) và cung cấp một độ nét phương ngang rất cao (1200px) để không bị lỗi từ chối.
- **Line 53 & 91:** `final_size = (1200, 1800)`
- **Line 54 & 92:** Resize ảnh cuối cùng về đúng `final_size` bằng thuật toán nén chất lượng cao LANCZOS.

## 2. Diện tích khuôn mặt chiếm khoảng 75% ảnh
**Yêu cầu:** Khuôn mặt người phải chiếm đa số không gian bức ảnh (khoảng 75%).
**Thực thi trong Code:**
Thuật toán AI (Haar Cascades) sẽ tìm hộp giới hạn (Bounding Box) của khuôn mặt. Hộp này bao gồm từ trán xuống cằm. Hệ thống tính toàn bộ chiều cao của đầu là gấp 1.4 lần khuôn mặt. Từ chiều cao đầu, hệ thống suy ngược ra chiều cao của tổng thể bức ảnh sao cho đầu chiếm đúng 75%.
- **Line 60-62:** `(x, y, w, h) = faces[0]` (Trích xuất kích thước khuôn mặt thực tế).
- **Line 75:** `head_height = h * 1.4` (Tính kích thước phần đầu).
- **Line 78-79:** `new_height = int(head_height / 0.75)` và tính `new_width` tương ứng (Scale khung ảnh sao cho đầu bằng chính xác 75%).

## 3. Khoảng cách Mắt đến đỉnh = 2/3 khoảng cách Mắt đến đáy
**Yêu cầu:** Chiều cao từ mắt lên mép trên của ảnh xấp xỉ 2/3 chiều cao từ mắt xuống mép dưới của ảnh.
**Thực thi trong Code:**
Về mặt toán học: Đỉnh đến Mắt (y) = 2/3 * Mắt đến Đáy (H - y) => 3y = 2H - 2y => 5y = 2H => **y = 0.4 * H**. (Khoảng cách từ mép trên xuống mắt bằng 40% tổng chiều cao ảnh).
- **Line 64-73:** Dùng AI nhận diện toạ độ đôi mắt và tính ra toạ độ trung bình `avg_eye_y`.
- **Line 81:** `target_eye_y = int(new_height * 0.4)` (Xác định vị trí lý tưởng của đôi mắt theo công thức 40%).
- **Line 86 & 89:** `paste_y = target_eye_y - avg_eye_y` (Dịch chuyển toàn bộ ảnh gốc lên/xuống sao cho mắt khớp hoàn toàn vào toạ độ lý tưởng).

## 4. Phông nền trắng tuyệt đối
**Yêu cầu:** Ảnh phải sử dụng phông nền trắng.
**Thực thi trong Code:**
- **Line 21:** `subject_data = remove(input_data)` (Sử dụng model AI `rembg` để tự động bóc tách và xoá phông nền cũ).
- **Line 27-29:** `white_bg = Image.new("RGBA", subject_pil.size, (255, 255, 255, 255))` (Tạo ra một bảng nền màu trắng tinh mã HEX #FFFFFF và dán người lên).

## 5. Độ phân giải 300 DPI và Định dạng JPEG 2000 (.jp2)
**Yêu cầu:** Hệ thống yêu cầu độ phân giải tối thiểu 300dpi và định dạng JPEG 2000.
**Thực thi trong Code:**
- **Line 101:** `final_img_pil.save(output_jpg_path, quality=100, dpi=(300, 300))` (Khóa cứng metadata của ảnh ở mức phân giải 300 DPI - chuẩn in ấn).
- **Line 105:** `final_img_pil.save(output_jp2_path, format="JPEG2000")` (Lệnh thư viện Pillow tự động encode file thành định dạng `.jp2` chuyên dụng thay vì JPG thông thường).

## Phụ lục 1: Nguồn gốc của `haarcascade_frontalface_default.xml` và `haarcascade_eye.xml`
Các file này không phải do hệ thống tự sinh ra mà là các **mô hình học máy (Machine Learning models) đã được huấn luyện sẵn** và được tích hợp trực tiếp bên trong thư viện lõi **OpenCV**. Khi cài đặt thư viện (`pip install opencv-python`), chúng sẽ tự động được tải về hệ thống (truy xuất qua biến môi trường `cv2.data.haarcascades`).

**Quá trình tạo ra các file này (Dựa trên Thuật toán Viola-Jones kinh điển):**
1. **Thu thập dữ liệu:** Hàng ngàn bức ảnh có chứa khuôn mặt/đôi mắt (Positive) và không chứa khuôn mặt (Negative) được thu thập.
2. **Trích xuất Haar Features:** Thuật toán quét ảnh để tìm các vùng tương phản sáng/tối đặc trưng của con người (ví dụ: hốc mắt thường tối hơn trán, sống mũi sáng hơn hai bên má).
3. **Huấn luyện mô hình:** Sử dụng thuật toán học máy AdaBoost để chọn lọc ra các đặc điểm quan trọng nhất trong hàng triệu đặc điểm.
4. **Đóng gói file XML:** Toàn bộ kết quả huấn luyện (gồm các trọng số, các quy tắc và cây quyết định) được lưu lại dưới dạng file XML siêu nhẹ. Nhờ vậy, chương trình `make_passport_photo.py` có thể nhận diện khuôn mặt và đôi mắt cực nhanh mà không cần phải tự "học" lại từ đầu hay yêu cầu máy tính cấu hình cao.

## Phụ lục 2: Cơ chế bóc tách nền và đè phông trắng của thư viện `rembg`
Để giải quyết yêu cầu **Phông nền trắng tuyệt đối**, hệ thống kết hợp 2 giai đoạn (Tương ứng với các dòng từ 21 đến 29):

### Giai đoạn 1: AI `rembg` bóc tách nền thành trong suốt
- **Thuật toán lõi:** `rembg` sử dụng một mạng nơ-ron học sâu có kiến trúc tên là **U-2-Net** (chuyên dành cho bài toán *Salient Object Detection* - Phát hiện chủ thể nổi bật).
- **Cách hoạt động:** Khi đưa bức ảnh vào, U-2-Net phân tích để nhận diện đâu là "tiền cảnh" (con người) và đâu là "hậu cảnh" (bức tường, cây cối, rèm cửa...). 
- **Kết quả trả về:** Mô hình tạo ra một kênh Alpha (kênh trong suốt). Các điểm ảnh thuộc về hậu cảnh sẽ bị biến thành trong suốt (độ mờ = 0).

### Giai đoạn 2: Kỹ thuật đè ảnh lên nền trắng (Alpha Compositing)
Vì `rembg` chỉ trả về ảnh có nền trong suốt (chứ không tự động bôi trắng nền), hệ thống sử dụng thư viện xử lý ảnh Pillow để thực hiện kỹ thuật **Alpha Masking**:
1. Đầu tiên, một tờ giấy trắng tinh khôi được tạo ra (`(255, 255, 255, 255)`).
2. Khi dùng lệnh dán (`paste`), ảnh trong suốt đóng vai trò làm **mặt nạ (mask)**.
3. Thuật toán sẽ quét qua ảnh gốc: nếu điểm ảnh đó trong suốt thì bỏ qua (giữ lại màu trắng của giấy); nếu điểm ảnh đục (là con người) thì sẽ in đè màu lên tờ giấy.
4. Cuối cùng, hệ thống dùng lệnh `convert("RGB")` để xóa bỏ hoàn toàn đặc tính trong suốt, hợp nhất (flatten) con người và phông trắng thành một bức ảnh solid duy nhất. Nhờ vậy, các chi tiết khó như viền tóc sẽ hòa trộn rất mượt mà vào nền trắng mà không bị viền lem nhem (halo effect).
