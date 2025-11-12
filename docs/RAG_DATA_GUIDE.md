# Hướng dẫn dữ liệu RAG VietSaga
Mục tiêu: xây dựng kho tư liệu lịch sử chính thống, chuẩn hoá để sử dụng với FAISS + OpenAI embedding. Toàn bộ tài liệu, metadata, manifest phải bằng tiếng Việt.

## 1. Danh mục nguồn ưu tiên
| Nhóm nguồn | Ví dụ | Ghi chú |
| --- | --- | --- |
| Cơ quan nhà nước | Cổng thông tin Chính phủ, Cục Văn thư & Lưu trữ, Thư viện Quốc gia | Độ tin cậy cao, ghi rõ giấy phép |
| Bảo tàng/di tích | Bảo tàng Lịch sử Quốc gia, Trung tâm Hoàng thành Thăng Long | Thường có bài viết mô tả, chú thích ảnh |
| Sách giáo khoa & tài liệu mở | SGK Lịch sử 10, 11 GDPT 2018; tài liệu Bộ GD công bố | Chỉ trích phần được phép, ghi rõ nguồn |
| Wiki uy tín | vi.wikipedia.org kèm nguồn dẫn | Dùng khi chưa có nguồn chính thống hơn |

Luôn lưu `source_url` đầy đủ, ngày tải về, và ghi chú giấy phép (nếu có).

## 2. Chuẩn hoá nội dung Markdown
1. Một file = một chủ đề (triều đại, sự kiện, nhân vật, địa danh).
2. Cấu trúc mẫu:
   ```markdown
   # Nhà Lý – Chiếu dời đô
   ## Bối cảnh
   ## Nội dung chính
   ## Ảnh hưởng
   ## Nguồn tham khảo
   - https://...
   ```
3. Ngôn ngữ: tiếng Việt, tránh lạm dụng Hán-Việt khó hiểu; nếu bắt buộc, thêm chú giải.
4. Số liệu/năm tháng giữ nguyên chính tả, thêm chú thích `(cần kiểm chứng)` nếu nguồn không thống nhất.
5. Lưu file tại `data/processed/<slug>.md`.

## 3. Chunking & overlap
- Dùng tokenizer `tiktoken` model `gpt-4o-mini`.
- Kích thước chunk: **500–800 tokens** (~350–550 từ).
- Overlap: **100–150 tokens** để không đứt mạch.
- Đặt `chunk_id` dạng `<slug>-<index>` (ví dụ `ly-chieu-do-0001`).

## 4. Metadata bắt buộc
```json
{
  "id": 0,
  "chunk_id": "ly-chieu-do-0001",
  "text": "...",
  "source": "https://thuvienlichsu.vn/chieu-doi-do",
  "period": "Ly",
  "type": "event",
  "year_range": "1009-1010",
  "tags": ["dời đô", "Thăng Long"],
  "location": "Hoa Lư, Thăng Long"
}
```
Quy ước `period`: `HongBang`, `BacThuoc`, `Ly`, `Tran`, `LeSo`, `Nguyen`, `CanDai`, `HienDai` (khớp agent ID).

## 5. Quy trình ingest chuẩn
1. **Thu thập**: tải HTML/PDF về `data/raw/<nguon>`.
2. **Tiền xử lý**: convert sang Markdown bằng Pandoc hoặc script Python, xoá quảng cáo, footnote không cần thiết.
3. **Chuẩn hoá**: áp dụng cấu trúc heading, kiểm tra chính tả, thêm chú thích nguồn.
4. **Chunking**: script `python scripts/chunk_markdown.py data/processed` → `chunks.jsonl`.
5. **Embedding**: gọi OpenAI `text-embedding-3-large`, lưu vector float32. Script nên hỗ trợ batch + retry.
6. **Xây dựng FAISS**: dùng `faiss.IndexFlatIP` (hoặc IVF tuỳ quy mô), lưu `faiss.index`.
7. **Metadata & manifest**:
   - `meta.json`: map id → metadata.
   - `rag_manifest.json` ví dụ:
     ```json
     {
       "version": "2025-02-01",
       "docs_count": 1024,
       "embedding_model": "text-embedding-3-large",
       "notes": "Batch triều Lý/Trần",
       "checksum": "sha256:..."
     }
     ```

## 6. Kiểm định chất lượng
- Kiểm tra ngẫu nhiên ≥10% chunk: đúng nguồn, không lỗi chính tả nghiêm trọng, có ít nhất một mốc thời gian rõ.
- Đảm bảo cùng một sự kiện không bị trùng chunk (so sánh hash text).
- Khi agent trả lời thiếu chính xác, ghi lại `query`, tìm chunk tương ứng, bổ sung hoặc chỉnh metadata.

## 7. Tích hợp với prompt `[CONTEXT]`
- Khi gọi OpenAI, backend format:
  ```
  [CONTEXT]
  (doc#12 | Tran | Chiếu dời đô)
  ...nội dung rút gọn...
  ```
- Chỉ đưa tối đa 4 đoạn, mỗi đoạn ≤ 1200 ký tự.
- Nếu không có doc phù hợp (`rag_hits=0`), backend phải chèn thông điệp “Không có tư liệu kèm theo” để agent báo lại cho người dùng.

## 8. Bảo mật & bản quyền
- Chỉ dùng dữ liệu được phép trích dẫn. Nếu nghi ngờ, xin phép hoặc loại bỏ.
- Không lưu thông tin cá nhân hiện đại nếu không phục vụ mục đích học thuật.
- Manifest cần ghi chú nguồn có điều kiện cấp phép đặc biệt.

## 9. Tự động hoá & vận hành
- Script ingest nên hỗ trợ tham số `--period`, `--source`, `--resume`.
- Lưu log quá trình embed để theo dõi chi phí/token.
- Sau mỗi lần build, chạy `/admin/rag/health` để đảm bảo backend đọc được index/meta.
- Sao lưu `faiss.index` + `meta.json` + `rag_manifest.json` vào S3/Drive ngay sau khi tạo.

## 10. Roadmap dữ liệu
| Mốc | Nội dung |
| --- | --- |
| V1 | 30–50 chủ đề triều Lý, Trần, Lê sơ, kháng Nguyên |
| V1.1 | Bổ sung cận đại & hiện đại, hoàn thiện quest theo chủ đề |
| V2 | Chuyển RAG sang Postgres + pgvector để lọc metadata nâng cao |
| V3 | Thêm reranker (cross-encoder) + cache kết quả phổ biến |
