# Tài liệu Task Scripts

Tất cả script đều nhận tham số qua CLI (`--ten_tham_so gia_tri`) và in kết quả ra stdout.
Chạy trực tiếp: `python tasks/<script>.py --help`

---

## ⚙ Hệ thống

### `sysinfo.py`
In thông tin hệ thống: OS, CPU, RAM, Python version.
> Không cần tham số.

---

### `check_disk.py`
Kiểm tra dung lượng ổ đĩa. Tự động quét toàn bộ ổ đĩa trên máy kèm thanh hiển thị %.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--path` | Ổ đĩa hoặc thư mục cần kiểm tra | `C:\` |

---

### `kill_port.py`
Tìm và dừng tiến trình đang chiếm một cổng mạng. Hỗ trợ Windows (`taskkill`) và Linux/macOS (`kill`).

| Tham số | Mô tả | Bắt buộc |
|---------|-------|---------|
| `--port` | Số cổng cần giải phóng | ✓ |

**Ví dụ:** Giải phóng cổng 8080 đang bị chiếm bởi server cũ chưa tắt.

---

### `tail_log.py`
Đọc và in N dòng cuối cùng của một file log, kèm thông tin kích thước file.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--log_file` | Đường dẫn file log | *(bắt buộc)* |
| `--lines` | Số dòng hiển thị | `100` |

---

### `countdown.py`
Đếm ngược và hiển thị thông báo khi hết giờ. Hữu ích nhắc nhở họp, break, deploy window.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--seconds` | Số giây đếm ngược | *(bắt buộc)* |
| `--message` | Thông báo khi xong | `Done!` |

---

## 🌿 Git & Phiên bản

### `git_pull_all.py`
Duyệt toàn bộ thư mục con có `.git` và chạy `git pull` cho từng repo. In kết quả rõ ràng từng repo.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--repos_dir` | Thư mục chứa các repo | *(bắt buộc)* |
| `--branch` | Nhánh cần pull | *(mặc định của repo)* |

**Ví dụ:** Đầu ngày pull cùng lúc 10 repo của team về latest.

---

### `git_log_today.py`
Lấy toàn bộ commit trong ngày hôm nay của một repo. Có thể lọc theo tác giả cụ thể.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--repo_path` | Thư mục repo | *(bắt buộc)* |
| `--author` | Tên tác giả cần lọc | *(tất cả)* |

---

### `create_release.py`
Tạo git annotated tag và push lên remote. Kiểm tra tag chưa tồn tại trước khi tạo.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--repo_path` | Thư mục repo | *(bắt buộc)* |
| `--version` | Tên tag, vd: `v1.2.3` | *(bắt buộc)* |
| `--message` | Ghi chú release | `Release <version>` |

---

### `generate_changelog.py`
Sinh CHANGELOG từ git log, nhóm theo ngày. Có thể giới hạn từ một tag cụ thể và xuất ra file.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--repo_path` | Thư mục repo | *(bắt buộc)* |
| `--since_tag` | Chỉ lấy commit sau tag này | *(tất cả)* |
| `--output` | File xuất kết quả | `CHANGELOG.md` |

---

## 🧪 Build & Kiểm thử

### `run_tests.py`
Chạy bộ kiểm thử trong thư mục dự án. Hỗ trợ bất kỳ lệnh test nào (pytest, unittest, jest…).

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--project_path` | Thư mục dự án | *(bắt buộc)* |
| `--test_command` | Lệnh chạy test | `pytest` |
| `--verbose` | Hiển thị chi tiết | `True` |

---

### `run_linter.py`
Chạy linter kiểm tra chất lượng code. Exit code phản ánh kết quả (0 = không lỗi).

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--project_path` | Thư mục dự án | *(bắt buộc)* |
| `--linter` | `flake8` / `pylint` / `ruff` / `eslint` | `flake8` |

---

### `check_deps.py`
Liệt kê các package lỗi thời cần cập nhật. Hỗ trợ pip, npm, yarn, pnpm.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--project_path` | Thư mục dự án | *(bắt buộc)* |
| `--manager` | `pip` / `npm` / `yarn` / `pnpm` | `pip` |

---

### `clean_build.py`
Xóa các thư mục build artifact: `build/`, `dist/`, `__pycache__/`, `.pytest_cache/`, `node_modules/.cache/`… Có chế độ dry-run để xem trước trước khi xóa thật.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--project_path` | Thư mục dự án | *(bắt buộc)* |
| `--dry_run` | Xem trước, không xóa thật | `True` |

---

## 🚀 Deploy & Hạ tầng

### `deploy.py`
Template script deploy. Mặc định in các bước gợi ý; chỉnh sửa file để thêm lệnh thật của dự án.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--environment` | `staging` / `production` / `dev` | *(bắt buộc)* |
| `--version` | Branch hoặc phiên bản | `main` |
| `--confirm` | Cảnh báo khi deploy production | `True` |

> **Tuỳ chỉnh:** Điền lệnh deploy thực tế vào dict `DEPLOY_SCRIPTS` trong file.

---

### `check_api_health.py`
Gửi HTTP GET đến endpoint và kiểm tra status code. In response body (JSON được format đẹp).

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--url` | URL endpoint | *(bắt buộc)* |
| `--expected_status` | HTTP status mong đợi | `200` |
| `--timeout` | Timeout tính bằng giây | `10` |

---

### `docker_status.py`
In trạng thái container đang chạy, danh sách image, và dung lượng Docker chiếm trên disk.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--show_all` | Hiển thị cả container đã dừng | `False` |

> Yêu cầu: Docker đã được cài đặt và đang chạy.

---

### `backup_db.py`
Sao lưu database ra file với timestamp. Hỗ trợ PostgreSQL (`pg_dump`), MySQL (`mysqldump`), SQLite (copy file), MongoDB (`mongodump`).

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--db_type` | `postgresql` / `mysql` / `sqlite` / `mongodb` | *(bắt buộc)* |
| `--db_name` | Tên database | *(bắt buộc)* |
| `--output_path` | Thư mục lưu file backup | *(bắt buộc)* |

> Yêu cầu: CLI tương ứng phải có trong PATH (`pg_dump`, `mysqldump`…).

---

### `backup.py`
Sao lưu toàn bộ thư mục nguồn sang thư mục đích, tuỳ chọn nén thành file `.zip`.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--source` | Thư mục nguồn | *(bắt buộc)* |
| `--destination` | Thư mục đích | *(bắt buộc)* |
| `--compress` | Nén thành ZIP | `True` |

---

## 📡 Mạng & Kết nối

### `ping_host.py`
Ping một địa chỉ host và hiển thị kết quả từng gói, thống kê mất gói.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--host` | Host hoặc IP cần ping | *(bắt buộc)* |
| `--count` | Số lần ping | `4` |

---

### `open_ssh.py`
Mở kết nối SSH trong cửa sổ terminal mới. Hỗ trợ xác thực bằng password hoặc SSH key.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--host` | Địa chỉ server | *(bắt buộc)* |
| `--user` | Username | `root` |
| `--port` | Cổng SSH | `22` |
| `--key_file` | Đường dẫn file SSH private key | *(dùng password)* |

---

### `http_request.py`
Gửi HTTP request tùy chỉnh và in response đầy đủ. JSON được format tự động.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--url` | URL đích | *(bắt buộc)* |
| `--method` | `GET` / `POST` / `PUT` / `DELETE` / `PATCH` | `GET` |
| `--headers` | Headers dạng JSON string | `{}` |
| `--body` | Request body dạng JSON string | *(rỗng)* |

---

## 📊 Báo cáo & Giao tiếp

### `standup_report.py`
Quét tất cả repo trong thư mục, tổng hợp commit hôm nay nhóm theo từng thành viên. Dùng để báo cáo standup hàng ngày.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--repos_dir` | Thư mục chứa các repo | *(bắt buộc)* |
| `--output_format` | `text` / `markdown` / `html` | `markdown` |

---

### `send_slack.py`
Gửi thông báo đến Slack qua Incoming Webhook. Cần tạo webhook tại *Slack App Settings → Incoming Webhooks*.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--webhook_url` | URL webhook của Slack | *(bắt buộc)* |
| `--message` | Nội dung tin nhắn | *(bắt buộc)* |
| `--username` | Tên hiển thị của bot | `Dashboard Bot` |

---

### `env_check.py`
So sánh file `.env` với `.env.example`, phát hiện biến bị thiếu, biến rỗng, và biến thừa. Hữu ích khi onboard developer mới hoặc deploy sang môi trường mới.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--project_path` | Thư mục dự án | *(bắt buộc)* |

---

## 🗂 File & Dữ liệu

### `rename_files.py`
Đổi tên hàng loạt file theo pattern regex và thêm tiền tố. Có chế độ dry-run xem trước.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--folder` | Thư mục chứa file | *(bắt buộc)* |
| `--pattern` | Regex filter tên file | `.*` |
| `--prefix` | Tiền tố thêm vào tên | *(rỗng)* |
| `--dry_run` | Xem trước, không đổi thật | `True` |

---

### `find_large_files.py`
Quét đệ quy để tìm các file chiếm nhiều dung lượng nhất. Hiển thị danh sách top N kèm kích thước.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--directory` | Thư mục cần quét | *(bắt buộc)* |
| `--min_size_mb` | Ngưỡng kích thước tối thiểu (MB) | `100` |
| `--top_n` | Số lượng file hiển thị | `20` |

---

### `compare_folders.py`
So sánh nội dung hai thư mục bằng MD5 checksum. Phân loại file thành: chỉ trong A, chỉ trong B, khác nhau, giống nhau.

| Tham số | Mô tả | Mặc định |
|---------|-------|---------|
| `--folder_a` | Thư mục A | *(bắt buộc)* |
| `--folder_b` | Thư mục B | *(bắt buộc)* |
| `--show_same` | Hiển thị file giống nhau | `False` |

---

*Tài liệu này được tạo tự động. Cập nhật khi thêm task mới.*
