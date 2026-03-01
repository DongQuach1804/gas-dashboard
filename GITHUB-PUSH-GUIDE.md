# 🚀 Push to GitHub - Complete Guide

## Bước 1: Cấu hình Git (chỉ làm 1 lần)

```powershell
# Cấu hình toàn cục (áp dụng cho tất cả repo)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Hoặc chỉ cho repo này
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

## Bước 2: Add và Commit

```powershell
# Add tất cả files
git add .

# Commit với message
git commit -m "Initial commit: Gas Monitoring System with ML predictions"

# Kiểm tra status
git status
```

## Bước 3: Tạo Repository trên GitHub

1. Truy cập: https://github.com/new
2. **Repository name**: `gas-dashboard`
3. **Description**: `Smart gas monitoring system with ML predictions and Telegram alerts`
4. **Visibility**: Chọn Public hoặc Private
5. **⚠️ QUAN TRỌNG**: 
   - ❌ **KHÔNG** check "Add a README file"
   - ❌ **KHÔNG** check "Add .gitignore"
   - ❌ **KHÔNG** choose a license
6. Click **"Create repository"**

## Bước 4: Kết nối với GitHub

```powershell
# Thay YOUR_USERNAME bằng username GitHub của bạn
git remote add origin https://github.com/YOUR_USERNAME/gas-dashboard.git

# Đặt tên branch chính là 'main'
git branch -M main

# Kiểm tra remote đã đúng chưa
git remote -v
```

## Bước 5: Push lên GitHub

```powershell
# Push lần đầu
git push -u origin main

# Sẽ yêu cầu đăng nhập:
# - Username: <your-github-username>
# - Password: <your-personal-access-token>
```

### 🔑 Tạo Personal Access Token (nếu cần)

GitHub không còn chấp nhận password thông thường. Bạn cần Personal Access Token:

1. Truy cập: https://github.com/settings/tokens
2. Click **"Generate new token (classic)"**
3. **Note**: `gas-dashboard-token`
4. **Expiration**: Chọn thời hạn (90 days hoặc No expiration)
5. **Scopes**: Check ✅ **repo** (full control)
6. Click **"Generate token"**
7. **⚠️ Copy token ngay** (chỉ hiển thị 1 lần!)
8. Dùng token này thay cho password khi push

## Bước 6: Verify

Kiểm tra repository trên GitHub:
```
https://github.com/YOUR_USERNAME/gas-dashboard
```

Bạn sẽ thấy:
- ✅ README.md với badge và documentation
- ✅ 16 files (không có data folders)
- ✅ ML models (.h5, .pkl)
- ✅ Docker configs
- ✅ Node-RED flows

## 🔄 Các lệnh Git sau này

```powershell
# Xem thay đổi
git status

# Add file mới hoặc đã sửa
git add .

# Commit
git commit -m "Update: mô tả thay đổi"

# Push lên GitHub
git push

# Pull từ GitHub
git pull

# Xem lịch sử commit
git log --oneline
```

## 🛡️ Files đã được bảo vệ (.gitignore)

✅ **Đã ignore (không push lên GitHub):**
- `nodered_data/` - Runtime data
- `influxdb_data/` - Database files
- `grafana_data/` - Dashboard data
- `.env`, `.env.*` - Environment variables
- `flows_cred.json` - Node-RED credentials
- `*.key`, `*.pem` - Security keys
- `.venv/` - Python virtual environment

## 📝 Tạo README.md badge (optional)

Thêm vào đầu README.md:

```markdown
![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
```

## 🆘 Xử lý lỗi

### Fatal: remote origin already exists
```powershell
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/gas-dashboard.git
```

### Push bị reject
```powershell
# Pull trước rồi push lại
git pull origin main --allow-unrelated-histories
git push -u origin main
```

### Cần đổi remote URL
```powershell
git remote set-url origin https://github.com/NEW_USERNAME/gas-dashboard.git
```

---

**Ready to push! 🚀**
