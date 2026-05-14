# CI Setup — kích hoạt GitHub Actions

GitHub OAuth token cho `gh` CLI mặc định không có scope `workflow`, nên
commit đầu tiên không thể tạo file ở `.github/workflows/`. File CI được
lưu tạm tại `deployment/ci.yml.template`.

## Kích hoạt CI

Sau khi refresh auth có scope `workflow`:

```bash
# 1. Refresh token với scope workflow
gh auth refresh -s workflow

# 2. Verify
gh auth status   # phải thấy "workflow" trong Token scopes

# 3. Move template về đúng chỗ
mkdir -p .github/workflows
git mv deployment/ci.yml.template .github/workflows/ci.yml

# 4. Commit + push
git add -A
git commit -m "ci: enable GitHub Actions"
git push
```

## Nội dung CI

Workflow chạy trên `ubuntu-latest`:

- `ruff check` + `ruff format --check`
- `mypy src` (strict mode)
- `pytest tests/unit` với `QT_QPA_PLATFORM=offscreen` cho Python 3.11 + 3.12

Xem nội dung tại [`ci.yml.template`](ci.yml.template).
