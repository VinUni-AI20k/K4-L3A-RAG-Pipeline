# Hiệu chỉnh SCORE_THRESHOLD

## In-domain

| Score | Query | Nguồn top-1 |
|---:|---|---|
| 0.6134 | Thí sinh khu vực 1 được cộng bao nhiêu điểm ưu tiên? | `quyet_dinh_955_2026_quy_che_tuyen_sinh_dhqghn.pdf` |
| 0.6785 | Chỉ tiêu tuyển sinh được xác định theo năng lực đào tạo như thế nào? | `thong_tu_06_2026_quy_che_tuyen_sinh.pdf` |
| 0.6555 | Các mốc thời gian quan trọng của kỳ tuyển sinh đại học 2026 là gì? | `02_tuyen_sinh_2026_cac_moc_thoi_gian_quan_trong_thi_sinh_can_nho.json` |
| 0.6603 | Thanh toán lệ phí xét tuyển đại học trực tuyến bằng cách nào? | `04_huong_dan_thanh_toan_truc_tuyen_le_phi_xet_tuyen_dai_hoc_2026.json` |
| 0.7387 | Quy chế tuyển sinh 2026 có những điểm mới nào? | `02_tuyen_sinh_2026_cac_moc_thoi_gian_quan_trong_thi_sinh_can_nho.json` |
| 0.6565 | Điều kiện để được xét tuyển thẳng vào đại học là gì? | `thong_tu_06_2026_quy_che_tuyen_sinh.pdf` |
| 0.7055 | Cách quy đổi điểm chứng chỉ ngoại ngữ khi xét tuyển? | `thong_tu_06_2026_quy_che_tuyen_sinh.pdf` |
| 0.6959 | Ngưỡng đầu vào đối với ngành đào tạo giáo viên được quy định ra sao? | `quyet_dinh_955_2026_quy_che_tuyen_sinh_dhqghn.pdf` |
| 0.6933 | Thí sinh được đăng ký tối đa bao nhiêu nguyện vọng? | `01_toan_van_cong_van_2304_bgddt_gddh_huong_dan_tuyen_sinh_dai_hoc_cao_dang_2026.json` |
| 0.6458 | Xét tuyển bằng học bạ được quy định thế nào trong quy chế? | `thong_tu_06_2026_quy_che_tuyen_sinh.pdf` |
| 0.6294 | Điểm thi đánh giá năng lực được sử dụng để xét tuyển ra sao? | `02_tuyen_sinh_2026_cac_moc_thoi_gian_quan_trong_thi_sinh_can_nho.json` |
| 0.7323 | Trách nhiệm của cơ sở đào tạo trong công bố đề án tuyển sinh là gì? | `thong_tu_06_2026_quy_che_tuyen_sinh.pdf` |

## Out-of-domain

| Score | Query | Nguồn top-1 |
|---:|---|---|
| 0.3157 | Cách đặt vé máy bay giá rẻ đi Đà Lạt? | `thong_tu_06_2026_quy_che_tuyen_sinh.pdf` |
| 0.3928 | Thời tiết Hà Nội ngày mai thế nào? | `04_huong_dan_thanh_toan_truc_tuyen_le_phi_xet_tuyen_dai_hoc_2026.json` |
| 0.4630 | Điểm chuẩn Đại học Bách Khoa Paris năm nay bao nhiêu? | `thong_tu_06_2026_quy_che_tuyen_sinh.pdf` |
| 0.3167 | Công thức nấu phở bò truyền thống? | `quyet_dinh_955_2026_quy_che_tuyen_sinh_dhqghn.pdf` |
| 0.2551 | Giá Bitcoin hôm nay là bao nhiêu? | `thong_tu_06_2026_quy_che_tuyen_sinh.pdf` |
| 0.4098 | Cách sửa lỗi màn hình xanh trên Windows 11? | `quyet_dinh_955_2026_quy_che_tuyen_sinh_dhqghn.pdf` |
| 0.3729 | Lịch thi đấu vòng loại World Cup 2026? | `05_nhung_diem_moi_trong_quy_che_tuyen_sinh_dai_hoc_2026.json` |
| 0.3209 | Triệu chứng của bệnh cúm A là gì? | `03_chinh_sach_uu_tien_trong_tuyen_sinh_dai_hoc.json` |
| 0.4442 | Thủ tục đăng ký kết hôn với người nước ngoài? | `01_toan_van_cong_van_2304_bgddt_gddh_huong_dan_tuyen_sinh_dai_hoc_cao_dang_2026.json` |
| 0.2766 | Nên mua xe máy điện hãng nào tốt nhất? | `quyet_dinh_955_2026_quy_che_tuyen_sinh_dhqghn.pdf` |

## Kết luận

- In-domain: min `0.6134`, trung vị `0.6694`
- Out-of-domain: max `0.4630`, trung vị `0.3469`
- Khoảng trống giữa hai cụm: `0.1503`
- **SCORE_THRESHOLD đề xuất: `0.54`** (fallback thừa: 0, bỏ sót refusal: 0, biên: 0.0734)
