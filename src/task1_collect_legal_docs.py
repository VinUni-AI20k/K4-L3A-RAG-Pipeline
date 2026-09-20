"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Hướng dẫn:
    1. Chọn chủ đề của nhóm.
    2. Tìm tối thiểu 3 tài liệu PDF/DOCX từ nguồn công khai.
    3. Lưu file gốc vào data/landing/legal/.
    4. Đặt tên không dấu và thể hiện đúng nội dung.

Ví dụ tài liệu: học phí, học bổng, ký túc xá, quy trình đăng ký.
Nếu website chặn crawler, hãy chọn nguồn công khai khác; không vượt WAF.
"""

from pathlib import Path
import requests

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tải ít nhất 3 PDF/DOCX từ nguồn công khai."""
    # TODO: Có thể tải thủ công hoặc dùng requests.
    sources = {
        "ielts_writing_task1_band_descriptors.pdf": "https://www.e-fellows.net/uploads/NEU-Dokumente/Writing-Band-descriptors-Task-1.pdf",
        "ielts_writing_task2_band_descriptors.pdf": "https://www.e-fellows.net/uploads/NEU-Dokumente/Writing-Band-descriptors-Task-2.pdf",
        "ielts_writing_examiner_feedback_criteria.pdf": "https://www.e-fellows.net/uploads/NEU-Dokumente/BC-IELTS-PT-4-AcWriting-FINAL_Feedback.pdf",
        "ielts_writing_model_answers_assessment.pdf": "https://www.e-fellows.net/uploads/NEU-Dokumente/BC-IELTS-PT-4-AcWriting-FINAL_Model-answer.pdf",
    }
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for filename, url in sources.items():
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        out_path = DATA_DIR / filename
        out_path.write_bytes(response.content)
        print(f"Saved: {out_path} ({len(response.content)} bytes)")


if __name__ == "__main__":
    setup_directory()
    download_documents()
