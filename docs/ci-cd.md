# CI/CD

Tài liệu này mô tả chuẩn kiểm tra trước khi push và workflow GitHub Actions hiện có.

## Workflow

File:

```text
.github/workflows/ci.yml
```

Trigger:

- `push` vào `main` hoặc `master`.
- `pull_request` vào `main` hoặc `master`.

## Job Hiện Có

Job `python-checks` chạy trên `windows-latest` để sát môi trường Windows/Git Bash đang phát triển.

Các bước:

1. Checkout source.
2. Cài Python 3.12.
3. Cài dependency từ `requirements.txt`.
4. Copy `.env.example` thành `.env`.
5. Compile toàn bộ file Python bằng `py_compile`.
6. Import FastAPI app bằng `from backend.main import app`.
7. Cài Node.js 20.
8. Cài frontend dependencies bằng `npm ci --prefix frontend`.
9. Typecheck frontend bằng `npm run typecheck --prefix frontend`.
10. Build frontend bằng `npm run build --prefix frontend`.
11. Validate production Compose bằng `docker compose config --quiet`.

CI dùng:

```text
NEXT_TELEMETRY_DISABLED=1
NEXT_DIST_DIR=.next-ci
```

để build frontend sạch, không dùng cache local `.next-rapi-local`.

## Lệnh Kiểm Tra Local

Python:

```powershell
$files = Get-ChildItem -Recurse -Filter *.py | Where-Object { $_.FullName -notmatch '\\.venv|__pycache__|\\.next|node_modules' } | ForEach-Object { $_.FullName }
python -m py_compile $files
python -c "from backend.main import app; print(app.title)"
```

Frontend:

```powershell
npm ci --prefix frontend
npm run typecheck --prefix frontend
npm run build --prefix frontend
```

Docker Compose:

```powershell
docker compose --env-file .env.example -f infra/docker-compose.production.yml config --quiet
```

Production env:

```powershell
python scripts/dev/validate_production_env.py
```

## Quy Tắc Merge

Chỉ merge/push lên branch chính khi:

- CI pass.
- Không commit `.env` hoặc secret thật.
- `.env.example` còn dùng placeholder an toàn.
- Frontend typecheck/build pass.
- Compose production validate pass.
- Các thay đổi camera/AI đã smoke test nếu ảnh hưởng runtime.
- Các thay đổi auth/users/RBAC đã test login và update role.

## Nâng Cấp CI/CD Đề Xuất

| Hạng mục | Lý do | Thời điểm bật |
|---|---|---|
| Ruff lint | Bắt lỗi Python sớm | Khi đã thống nhất style |
| Pytest backend/worker | Chống regression nghiệp vụ | Khi test suite ổn định |
| Frontend lint | Bắt lỗi React/Next | Khi ESLint config ổn định |
| Docker image build | Đảm bảo image build được | Trước release production |
| GHCR push | Lưu image versioned | Khi có release strategy |
| Staging deploy | Test trước production | Khi có server staging |
| Secret scanning | Chặn leak secret | Trước public repo |
| Dependency audit | Theo dõi CVE | Trước production thật |
| Release workflow | Deploy theo tag | Khi có quy trình release |

## Flow Làm Việc

```text
feature branch
  -> run local checks
  -> commit source/docs
  -> push branch
  -> GitHub Actions CI
  -> pull request review
  -> merge main/master
  -> release/deploy
```

## Checklist Trước Khi Push

```bash
git status --short
git diff --stat
git diff -- .env.example README.md docs/ .github/workflows/ci.yml
```

Không push:

- `.env`
- credential thật
- RTSP thật
- `.runtime/`
- `.next*`
- runtime snapshots/logs
- `admin_super_login.md` nếu chứa thông tin đăng nhập thật
