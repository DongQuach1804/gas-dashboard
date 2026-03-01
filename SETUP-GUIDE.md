# 🚀 Setup Guide - Gas Monitoring System

Hướng dẫn cài đặt và cấu hình hệ thống giám sát khí gas với ML predictions và Telegram alerts.

---

## 📋 Yêu Cầu Hệ Thống

- **OS**: Windows 10/11
- **Python**: 3.10+
- **Docker**: Docker Desktop (hoặc Docker CLI)
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 5GB free space

---

## 🔧 Cài Đặt Cơ Bản

### 1. Clone Repository

```powershell
git clone <repository-url>
cd gas-dashboard
```

### 2. Tạo Python Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Lỗi Execution Policy?**
```powershell
# Option 1: Bypass tạm thời
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# Option 2: Chạy Python trực tiếp
& .\.venv\Scripts\python.exe script.py
```

### 3. Cài Đặt Dependencies

```powershell
pip install -r requirements.txt

# Thêm cho Hybrid ML
pip install joblib scikit-learn
```

### 4. Start Docker Services

```powershell
docker-compose up -d

# Verify services
docker ps
# Expected: influxdb, nodered, grafana
```

---

## 🤖 ML Predictor Setup

### Option 1: LSTM Only (Đơn giản)

```powershell
# Start API
python ml_predictor_mocked.py

# API: http://localhost:8000
```

**Features:**
- ✅ 3 LSTM models (CO, Ethanol, Temperature)
- ✅ Regression predictions (0-1 values)
- ✅ ~40ms processing time

### Option 2: Hybrid LSTM + SVM (Chính xác hơn)

```powershell
# Start hybrid API
python ml_predictor_hybrid.py

# API: http://localhost:8000
```

**Features:**
- ✅ 3 LSTM models (CO, Ethanol, Temperature) - regression
- ✅ 1 SVM model (Temperature/Humidity) - classification
- ✅ Combined alert logic
- ✅ ~50ms processing time
- ✅ Ít false positive hơn

**Models Required:**
- `lstm_co_model.h5`
- `lstm_eth_model_gen.h5`
- `lstm_ht_model.h5`
- `svm_ht_model_downsampled_10x.pkl` (for hybrid only)
- `ht_sensor_scaler.pkl` (for hybrid only)

---

## 📱 Telegram Integration

### 1. Tạo Bot

```
1. Mở Telegram → Tìm @BotFather
2. Gửi: /newbot
3. Nhập tên bot: Gas Monitor Bot
4. Nhập username: your_gas_bot
5. Nhận TOKEN: 123456789:ABCdef...
```

### 2. Lấy Chat ID

```
1. Mở Telegram → Tìm @getidsbot
2. Click Start
3. Bot trả về: Your user ID: 123456789
4. Copy số này
```

### 3. Cài Package Node-RED

**Option A: Qua UI (Recommended)**
```
1. Node-RED → Menu (≡) → Manage palette
2. Tab "Install" → Search: node-red-contrib-telegrambot
3. Click Install → Restart Node-RED
```

**Option B: Qua Docker CLI**
```powershell
docker exec nodered npm install node-red-contrib-telegrambot
docker restart nodered
```

### 4. Cấu Hình Bot trong Node-RED

```
1. Import flow: nodered-flow-telegram.json
2. Double-click node "Send to Telegram"
3. Dropdown "Bot" → Add new telegram bot → Pencil icon
4. Tab "Connection":
   - Bot-Name: gas-monitor-bot
   - Token: [Paste token từ @BotFather]
5. Tab "Users":
   - Chat IDs: [Paste Chat ID từ @getidsbot]
   - Chỉ nhập số, VD: 123456789
6. Click "Add" (not Update)
7. Click "Done"
8. Deploy
9. Verify: Node có chấm xanh = success
```

### 5. Test Alert

```
1. Click button "Test Telegram Alert" trong Node-RED
2. Check Telegram app → Nhận message
```

---

## 🎛️ Grafana Dashboard

### 1. Access Grafana

```
URL: http://localhost:3000
User: admin
Password: adminpass
```

### 2. Import Dashboard

```
1. Grafana → Dashboards → Import
2. Upload file: grafana-dashboard-direct.json
3. Select datasource: InfluxDB
4. Click Import
```

### 3. Configure InfluxDB Datasource

```
URL: http://influxdb:8086
Database: gasdb
User: admin
Password: adminpass
```

---

## ⚙️ Configuration Files

### docker-compose.yml

```yaml
services:
  influxdb:
    image: influxdb:1.8
    ports: ["8086:8086"]
    environment:
      - INFLUXDB_DB=gasdb
      - INFLUXDB_ADMIN_USER=admin
      - INFLUXDB_ADMIN_PASSWORD=adminpass
    volumes:
      - ./influxdb_data:/var/lib/influxdb

  nodered:
    image: nodered/node-red:latest
    ports: ["1880:1880"]
    volumes:
      - ./nodered_data:/data

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    volumes:
      - ./grafana_data:/var/lib/grafana
```

### Node-RED Flow

**Files:**
- `nodered-flow-telegram.json` - Full Telegram integration
- `nodered-flow-ml-api.json` - ML API only (no Telegram)

**Import:**
```
Node-RED → Menu → Import → Select file → Deploy
```

---

## 🔄 API Management

### Start API (Foreground)

```powershell
# LSTM only
python ml_predictor_mocked.py

# Hybrid LSTM + SVM
python ml_predictor_hybrid.py
```

### Start API (Background)

```powershell
# LSTM only
Start-Process python -ArgumentList "ml_predictor_mocked.py" -WindowStyle Hidden

# Hybrid
Start-Process python -ArgumentList "ml_predictor_hybrid.py" -WindowStyle Hidden
```

### Stop API

```powershell
# Find and kill
Get-Process python | Where-Object {$_.CommandLine -like "*ml_predictor*"} | Stop-Process -Force
```

### Check API Status

```powershell
# Health check
Invoke-RestMethod http://localhost:8000/health

# Models info
Invoke-RestMethod http://localhost:8000/models
```

### Test Prediction

```powershell
$body = @{MQ135=250; MQ5=150} | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/predict -Method Post -Body $body -ContentType "application/json"
```

---

## 🚨 Alert Thresholds

### LSTM Only Mode

| Condition | Level | Action |
|-----------|-------|--------|
| CO > 0.7 | 🚨 DANGER | Telegram alert |
| Ethanol > 0.6 | ⚠️ WARNING | Telegram alert |
| Temperature > 0.8 | ⚠️ WARNING | Telegram alert |
| All OK | ✅ NORMAL | No alert |

### Hybrid Mode (LSTM + SVM)

| Condition | Level | Action |
|-----------|-------|--------|
| CO > 0.7 OR Temp > 0.8 OR SVM=DANGER | 🚨 DANGER | Telegram alert |
| CO > 0.5 OR Ethanol > 0.6 OR Temp > 0.6 OR SVM=WARNING | ⚠️ WARNING | Telegram alert |
| All OK AND SVM=NORMAL | ✅ NORMAL | No alert |

**Customize thresholds:**
```python
# Edit ml_predictor_hybrid.py
CO_THRESHOLD_DANGER = 0.7
CO_THRESHOLD_WARNING = 0.5
ETHANOL_THRESHOLD_WARNING = 0.6
```

---

## 📊 Data Flow

```
┌─────────────┐
│ MQ135 + MQ5 │ Sensors (Node-RED simulation every 10s)
└──────┬──────┘
       │
       v
┌─────────────┐
│  InfluxDB   │ Store sensor data (gas_data measurement)
└──────┬──────┘
       │ (Last 20 timesteps)
       v
┌─────────────┐
│  ML API     │ LSTM/SVM predictions
└──────┬──────┘
       │
       ├──→ InfluxDB (gas_predictions measurement)
       │
       └──→ Telegram (if alert triggered)
```

---

## 🔍 Verification Checklist

### ✅ Docker Services

```powershell
docker ps
# Expected: 3 running containers
```

### ✅ InfluxDB Data

```powershell
# Check measurements
Invoke-RestMethod "http://localhost:8086/query?db=gasdb&q=SHOW MEASUREMENTS" `
    -Headers @{'Authorization'='admin:adminpass'}

# Expected: gas_data, gas_predictions
```

### ✅ ML API

```powershell
Invoke-RestMethod http://localhost:8000/health
# Expected: {"status":"healthy","models_loaded":true}
```

### ✅ Node-RED Flow

```
1. Access: http://localhost:1880
2. See "ML Predictor + Telegram Alerts" tab
3. All nodes có màu xanh/xám (không có đỏ)
```

### ✅ Grafana Dashboard

```
1. Access: http://localhost:3000
2. Dashboards → Gas Monitoring Dashboard
3. See 10 panels with data
```

### ✅ Telegram Alerts

```
1. Node-RED → Click "Test Telegram Alert"
2. Check Telegram app → Receive formatted message
```

---

## 🎯 Quick Start Summary

**Minimum setup (5 minutes):**

```powershell
# 1. Start services
docker-compose up -d

# 2. Start API
python ml_predictor_mocked.py

# 3. Access dashboards
# Node-RED: http://localhost:1880
# Grafana: http://localhost:3000
```

**Full setup with Telegram (10 minutes):**

```powershell
# 1. Docker + API (same as above)
docker-compose up -d
python ml_predictor_hybrid.py

# 2. Telegram bot
# - Create bot: @BotFather
# - Get Chat ID: @getidsbot

# 3. Node-RED
# - Install: node-red-contrib-telegrambot
# - Import: nodered-flow-telegram.json
# - Config bot (Token + Chat ID)
# - Deploy

# 4. Test alert
# Click "Test Telegram Alert" button
```

---

## 📚 Next Steps

1. **Monitor system**: Check Grafana dashboard for real-time data
2. **Customize thresholds**: Edit alert levels in code
3. **Add sensors**: Replace mock data with real sensor integration
4. **Retrain models**: Update LSTM/SVM with new data
5. **Scale up**: Add more prediction models or alert channels

---

## 🆘 Need Help?

See **TROUBLESHOOTING.md** for common issues and solutions.

**Quick fixes:**
- Docker not found → Install Docker Desktop
- API errors → Check `requirements.txt` installed
- Telegram not working → Verify bot token and Chat ID
- No data in Grafana → Wait 3-4 minutes for data collection
- Node-RED errors → Restart: `docker restart nodered`

---

✅ **Setup complete! Hệ thống đã sẵn sàng giám sát.**
