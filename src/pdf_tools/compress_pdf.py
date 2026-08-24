import os
import sys
import subprocess
import shutil

def check_ghostscript():
    """Kiểm tra xem máy tính đã cài Ghostscript chưa"""
    if shutil.which('gs') is None:
        print("❌ Lỗi: Không tìm thấy công cụ Ghostscript trên máy (công cụ lõi để nén PDF).")
        print("💡 Để sử dụng tool này, bạn cần cài đặt Ghostscript. Vui lòng mở Terminal và chạy lệnh sau:")
        print("    brew install ghostscript")
        sys.exit(1)

def compress_pdf(input_path, output_path, level='ebook'):
    """
    Nén file PDF sử dụng Ghostscript.
    Các mức nén (level):
    - screen: Chất lượng thấp nhất, dung lượng nhỏ nhất (72 dpi). Dùng để chia sẻ qua mạng, đọc trên màn hình.
    - ebook: Chất lượng trung bình, dung lượng nhỏ (150 dpi). Khuyên dùng, cân bằng tốt giữa chất lượng và dung lượng.
    - printer: Chất lượng cao, dung lượng lớn hơn (300 dpi). Thích hợp để in ấn thông thường.
    - prepress: Chất lượng cực cao, bảo toàn màu sắc (300 dpi). Chuẩn in ấn chuyên nghiệp.
    - default: Mức nén mặc định của hệ thống.
    """
    check_ghostscript()
    
    if not os.path.exists(input_path):
        print(f"Lỗi: Không tìm thấy file gốc '{input_path}'")
        return

    valid_levels = ['screen', 'ebook', 'printer', 'prepress', 'default']
    if level not in valid_levels:
        print(f"⚠️ Cảnh báo: Mức nén '{level}' không tồn tại. Tự động chuyển về mức khuyên dùng 'ebook'.")
        print(f"Các mức hợp lệ: {', '.join(valid_levels)}")
        level = 'ebook'

    print(f"⏳ Đang nén file với chuẩn '{level}'...")
    
    gs_cmd = [
        'gs',
        '-sDEVICE=pdfwrite',
        '-dCompatibilityLevel=1.4',
        f'-dPDFSETTINGS=/{level}',
        '-dNOPAUSE',
        '-dQUIET',
        '-dBATCH',
        f'-sOutputFile={output_path}',
        input_path
    ]
    
    try:
        subprocess.run(gs_cmd, check=True)
        
        # Thống kê dung lượng
        original_size = os.path.getsize(input_path) / (1024 * 1024)
        new_size = os.path.getsize(output_path) / (1024 * 1024)
        
        print("\n✅ Nén PDF thành công!")
        print(f"📉 Dung lượng ban đầu: {original_size:.2f} MB")
        print(f"✨ Dung lượng sau nén: {new_size:.2f} MB (Tiết kiệm được {((original_size - new_size) / original_size * 100):.1f}%)")
        print(f"📁 File được lưu tại: {output_path}")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Lỗi trong quá trình nén PDF: Hệ thống báo lỗi {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("📖 CÁCH SỬ DỤNG:")
        print("python compress_pdf.py <file_gốc.pdf> <file_kết_quả.pdf> [chuẩn_nén]")
        print("\n[chuẩn_nén] hỗ trợ các loại sau:")
        print("  - screen   : Dung lượng nhỏ nhất (72 dpi) - Thích hợp gửi email")
        print("  - ebook    : Cân bằng nhất (150 dpi) - Khuyên dùng (MẶC ĐỊNH)")
        print("  - printer  : Dành để in ấn cơ bản (300 dpi)")
        print("  - prepress : Dành để in ấn chuyên nghiệp (300 dpi)")
        print("  - default  : Mặc định của hệ thống")
        print("\nVí dụ: python compress_pdf.py input.pdf output.pdf screen")
        sys.exit(1)
        
    in_file = sys.argv[1]
    out_file = sys.argv[2]
    comp_level = sys.argv[3] if len(sys.argv) > 3 else 'ebook'
    
    compress_pdf(in_file, out_file, comp_level)
