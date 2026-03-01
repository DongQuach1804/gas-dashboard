# 🔧 Troubleshooting Guide

Common issues and solutions for Gas Monitoring System.

---

## 🐳 Docker Issues

### Docker không tìm thấy lệnh

**Error:**
```
docker : The term 'docker' is not recognized...
```

**Solution:**
```powershell
# 1. Cài Docker Desktop: https://www.docker.com/products/docker-desktop/
# 2. Restart PowerShell
# 3. Verify
docker --version
```

### Container không start

**Check status:**
```powershell
docker ps -a
```

**Restart containers:**
```powershell
docker-compose restart

# Hoặc stop/start cụ thể
docker restart influxdb
docker restart nodered
docker restart grafana
```

**Xem logs:**
```powershell
docker logs influxdb
docker logs nodered --tail 50
docker logs grafana -f  # Follow mode
```

### Port đã được sử dụng

**Error:**
```
Bind for 0.0.0.0:8086 failed: port is already allocated
```

**Solution:**
```powershell
# Tìm process đang dùng port
netstat -ano | findstr :8086

# Kill process
taskkill /PID <PID> /F

# Hoặc đổi port trong docker-compose.yml
ports: ["8087:8086"]  # Host:Container
```

---

## 🤖 ML API Issues

### API không start

**Error:**
```
ModuleNotFoundError: No module named 'tensorflow'
```

**Solution:**
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Model không load được

**Error:**
```
OSError: Unable to open file (unable to open file: name = 'lstm_co_model.h5')
```

**Solution:**
```powershell
# Check file tồn tại
ls *.h5

# Expected: lstm_co_model.h5, lstm_eth_model_gen.h5, lstm_ht_model.h5

# Nếu không có → Train models
python train_lstm_co.py
python train_lstm_eth_generator.py
# (or copy from backup)
```

### Keras serialization error

**Error:**
```
ValueError: Could not deserialize 'keras.metrics.mse'
```

**Solution:**
```python
# Edit ml_predictor_hybrid.py
# Ensure compile=False when loading
model = keras.models.load_model('lstm_co_model.h5', compile=False)
```

### Sklearn feature mismatch

**Error:**
```
ValueError: X has 9 features, but MinMaxScaler is expecting 10 features
```

**Solution:**
```python
# Verify feature generation matches scaler training
# SVM requires: R1-R8 + Temp + Humidity (10 features)
# LSTM temp requires: R2-R8 + Temp + Humidity (9 features)

# Use correct function
generate_mock_features_svm()  # 10 features for SVM
generate_mock_features_lstm_temp()  # 9 features for LSTM temp
```

### Pydantic validation error

**Error:**
```
PydanticDeprecatedSince20: .dict() method is deprecated
```

**Solution:**
```python
# Replace in code
# Old
response.dict()

# New
response.model_dump()
```

### API không response

**Check health:**
```powershell
Invoke-RestMethod http://localhost:8000/health
```

**Test prediction:**
```powershell
$body = @{MQ135=250; MQ5=150} | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/predict -Method Post -Body $body -ContentType "application/json"
```

**Restart API:**
```powershell
# Kill process
Get-Process python | Where-Object {$_.CommandLine -like "*ml_predictor*"} | Stop-Process -Force

# Restart
python ml_predictor_hybrid.py
```

---

## 📡 Node-RED Issues

### Node-RED không truy cập được

**Check container:**
```powershell
docker ps | findstr nodered
```

**Restart:**
```powershell
docker restart nodered
```

**Access:**
```
http://localhost:1880
```

### Flow không import được

**Error:**
```
Invalid JSON
```

**Solution:**
```
1. Mở file .json bằng text editor
2. Verify JSON syntax (no trailing commas, proper quotes)
3. Copy toàn bộ content
4. Node-RED → Import → Clipboard → Paste
```

### Node màu đỏ sau deploy

**Check errors:**
```
1. Click node màu đỏ
2. Xem error message
```

**Common fixes:**
```
- InfluxDB node: Check server connection
- HTTP request node: Verify URL (host.docker.internal:8000)
- Telegram node: Check bot config
```

### Không gửi data đến InfluxDB

**Verify measurement:**
```powershell
Invoke-RestMethod "http://localhost:8086/query?db=gasdb&q=SELECT * FROM gas_data LIMIT 5" `
    -Headers @{'Authorization'='admin:adminpass'}
```

**Check Node-RED debug:**
```
1. Add Debug node sau InfluxDB node
2. Deploy
3. Xem Debug panel (bug icon, góc phải)
```

### ECONNREFUSED khi gọi ML API

**Error:**
```
Error: connect ECONNREFUSED 127.0.0.1:8000
```

**Solution:**
```javascript
// Node-RED inside Docker container
// Change URL from localhost to host.docker.internal
url: "http://host.docker.internal:8000/predict"

// NOT: http://localhost:8000/predict
```

---

## 📱 Telegram Issues

### Bot không response

**Check bot token:**
```
1. Open @BotFather
2. Send: /mybots
3. Select your bot → API Token
4. Copy token
5. Node-RED → Telegram config → Paste token
```

**Test bot:**
```
1. Open Telegram app
2. Find your bot
3. Send: /start
4. Bot should respond
```

### Chat ID trống

**Error:**
```
TypeError: Cannot read property 'chatId' of undefined
```

**Solution:**
```javascript
// Node-RED function node
msg.payload = {
    type: "message",
    content: "Test alert",
    chatId: 123456789  // Your actual Chat ID
};
return msg;
```

**Lấy Chat ID:**
```
1. Telegram → @getidsbot
2. Click Start
3. Copy số ID
```

### Không nhận được alert

**Check node status:**
```
Node-RED → Telegram sender node có chấm xanh = OK
```

**Manual test:**
```
1. Click button "Test Telegram Alert"
2. Check Telegram app
```

**Check alert conditions:**
```javascript
// Trong Node-RED flow
if (msg.payload.alert_level === "DANGER" || msg.payload.alert_level === "WARNING") {
    // Send Telegram
}
// NORMAL không gửi alert
```

### Package không cài được

**Error:**
```
npm install node-red-contrib-telegrambot failed
```

**Solution:**
```powershell
# Cài trong Docker container
docker exec nodered npm install node-red-contrib-telegrambot

# Restart
docker restart nodered

# Verify
# Node-RED → Palette → Installed → node-red-contrib-telegrambot
```

---

## 📊 Grafana Issues

### Không login được

**Default credentials:**
```
URL: http://localhost:3000
User: admin
Password: adminpass
```

**Reset password:**
```powershell
docker exec -it grafana grafana-cli admin reset-admin-password newpassword
```

### Dashboard không hiển thị data

**Check datasource:**
```
1. Grafana → Configuration → Data Sources
2. Click InfluxDB → Test → "Data source is working"
```

**Verify InfluxDB data:**
```powershell
# Check measurements
Invoke-RestMethod "http://localhost:8086/query?db=gasdb&q=SHOW MEASUREMENTS" `
    -Headers @{'Authorization'='admin:adminpass'}

# Expected: gas_data, gas_predictions
```

**Wait for data collection:**
```
Node-RED generates data every 10 seconds.
Wait 3-4 minutes for sufficient data points.
```

**Check panel queries:**
```
1. Dashboard → Panel → Edit
2. Query tab → Verify measurement name
3. Try: SELECT * FROM "gas_data" LIMIT 10
```

### Datasource không connect

**Error:**
```
InfluxDB Error: Connection refused
```

**Solution:**
```
1. Configuration → Data Sources → InfluxDB
2. URL: http://influxdb:8086  (NOT localhost)
3. Database: gasdb
4. User: admin
5. Password: adminpass
6. Save & Test
```

### Dashboard import error

**Error:**
```
Dashboard validation failed
```

**Solution:**
```
1. Open grafana-dashboard-direct.json
2. Find/replace datasource UID
3. Import → Select datasource manually
```

---

## 💾 Data Issues

### InfluxDB không có data

**Check database:**
```powershell
# List databases
Invoke-RestMethod "http://localhost:8086/query?q=SHOW DATABASES" `
    -Headers @{'Authorization'='admin:adminpass'}

# Expected: _internal, gasdb
```

**Create database if missing:**
```powershell
Invoke-RestMethod "http://localhost:8086/query" `
    -Method POST `
    -Body "q=CREATE DATABASE gasdb" `
    -Headers @{'Authorization'='admin:adminpass'}
```

**Check retention policy:**
```powershell
Invoke-RestMethod "http://localhost:8086/query?db=gasdb&q=SHOW RETENTION POLICIES" `
    -Headers @{'Authorization'='admin:adminpass'}
```

### Data bị mất sau restart

**Verify volumes:**
```yaml
# docker-compose.yml
volumes:
  - ./influxdb_data:/var/lib/influxdb  # Persistent storage
```

**Check permissions:**
```powershell
# Data should persist in influxdb_data/
ls ./influxdb_data/data/gasdb/
```

---

## 🔐 PowerShell Execution Policy

### Script không chạy được

**Error:**
```
cannot be loaded because running scripts is disabled on this system
```

**Solution A: Temporary bypass**
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\.venv\Scripts\Activate.ps1
```

**Solution B: Direct Python**
```powershell
& .\.venv\Scripts\python.exe ml_predictor_hybrid.py
```

**Solution C: Permanent (Admin required)**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 🔍 Debugging Tips

### Enable verbose logging

**ML API:**
```python
# Edit ml_predictor_hybrid.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Node-RED:**
```
Add Debug nodes after each step
Deploy → View Debug panel
```

**Docker:**
```powershell
docker logs nodered -f --tail 100
```

### Network diagnostics

**Check container IPs:**
```powershell
docker inspect nodered -f "{{.NetworkSettings.IPAddress}}"
docker inspect influxdb -f "{{.NetworkSettings.IPAddress}}"
```

**Test connectivity from container:**
```powershell
docker exec nodered ping influxdb
docker exec nodered curl http://influxdb:8086/ping
```

### Performance monitoring

**Check CPU/RAM:**
```powershell
docker stats
```

**Check API response time:**
```powershell
Measure-Command {Invoke-RestMethod http://localhost:8000/predict -Method Post -Body '{"MQ135":250}' -ContentType "application/json"}
```

---

## 🆘 Still Need Help?

### System health check

```powershell
# 1. Docker containers
docker ps

# 2. ML API
Invoke-RestMethod http://localhost:8000/health

# 3. InfluxDB
Invoke-RestMethod "http://localhost:8086/ping"

# 4. Node-RED
Invoke-RestMethod "http://localhost:1880"

# 5. Grafana
Invoke-RestMethod "http://localhost:3000/api/health"
```

### Collect logs for debugging

```powershell
# Save all logs to file
docker logs influxdb > influxdb.log 2>&1
docker logs nodered > nodered.log 2>&1
docker logs grafana > grafana.log 2>&1

# Check API logs
python ml_predictor_hybrid.py > api.log 2>&1
```

### Reset everything

```powershell
# Stop and remove containers
docker-compose down

# Remove data (⚠️ Loses all data)
Remove-Item -Recurse -Force influxdb_data, nodered_data, grafana_data

# Restart
docker-compose up -d
```

---

✅ **Hết lỗi rồi! Chạy ngon lành!**

### 3. Kiểm tra Node-RED đang gửi data

1. Mở Node-RED: http://localhost:1880
2. Check flow có được **Deploy** chưa (nút Deploy màu đỏ = chưa deploy)
3. Bật Debug nodes và xem tab Debug (bên phải)
4. Kiểm tra status của nodes (dot màu xanh = OK)

### 4. Kiểm tra Grafana Data Source

1. Mở Grafana: http://localhost:3000
2. **Connections** → **Data sources**
3. Click vào InfluxDB datasource
4. Kiểm tra config:
   - URL: `http://influxdb:8086` (KHÔNG PHẢI localhost!)
   - Database: `gasdb`
   - Access: `Server (default)`
5. Click **Save & Test** → Phải thấy ✅ "Data source is working"

---

## 🐛 Các Lỗi Thường Gặp

### Lỗi 1: Grafana Dashboard trống (No data)

**Nguyên nhân:**
- InfluxDB không có data
- Data source chưa cấu hình đúng
- Time range không đúng
- Query sai

**Giải pháp:**

#### A. Check InfluxDB có data
```powershell
Invoke-RestMethod -Uri "http://localhost:8086/query?db=gasdb&q=SELECT+COUNT(*)+FROM+gas_data"
```

Nếu count = 0 hoặc lỗi → **Import flow test đơn giản:**

1. Download: `nodered-flow-simple-test.json`
2. Node-RED → Import → Deploy
3. Đợi 30 giây
4. Check lại data

#### B. Fix Grafana Data Source

**Lỗi: "Bad Gateway" hoặc "Network Error"**

URL sai! Phải dùng:
```
http://influxdb:8086  ✅ Đúng (Docker network)
http://localhost:8086 ❌ Sai (không connect được)
```

**Lỗi: "Database not found"**

Database name sai:
```
gasdb     ✅ Đúng
gas_db    ❌ Sai
GasDB     ❌ Sai (case-sensitive)
```

#### C. Fix Time Range

Dashboard có thể đang query quá khứ xa:

1. Click **time picker** (góc trên phải Grafana)
2. Chọn: **Last 15 minutes** hoặc **Last 1 hour**
3. Refresh dashboard

#### D. Fix Query

Mở panel edit và kiểm tra query:

**Query mẫu đúng:**
```sql
SELECT mean("MQ135") FROM "gas_data" 
WHERE $timeFilter 
GROUP BY time($__interval) fill(null)
```

**Lỗi thường gặp:**
- Measurement name sai: `gas_data` (không phải `gas-data` hoặc `gasdata`)
- Field name sai: `MQ135` (không phải `mq135` hoặc `Mq135`)

### Lỗi 2: Node-RED không gửi data vào InfluxDB

#### Check 1: InfluxDB node config

Double-click "InfluxDB out" node:

**Config phải là:**
```
Host: influxdb       ✅ (KHÔNG PHẢI localhost)
Port: 8086
Database: gasdb
Version: 1.8-flux
Username: (để trống)
Password: (để trống)
```

#### Check 2: Payload format

InfluxDB node cần payload dạng array:

```javascript
msg.payload = [
    {
        measurement: "gas_data",
        fields: {
            MQ135: 234.5,
            MQ5: 123.4
        }
    }
];
```

**SAI:**
```javascript
msg.payload = {MQ135: 234.5, MQ5: 123.4}; // ❌ Không phải array
```

#### Check 3: Deploy flow

Sau khi sửa flow:
1. Click nút **Deploy** (góc trên phải)
2. Đợi thông báo "Successfully deployed"
3. Kiểm tra node status (dot xanh bên dưới node)

### Lỗi 3: ML Predictor API không trả về kết quả

#### Check API đang chạy

```powershell
Invoke-RestMethod -Uri http://localhost:8000/health
```

**Nếu lỗi "Unable to connect":**
```powershell
# Start API
python ml_predictor_mocked.py
```

#### Check API có đủ data

API cần >= 20 timesteps trong InfluxDB:

```powershell
$count = (Invoke-RestMethod -Uri "http://localhost:8086/query?db=gasdb&q=SELECT+COUNT(*)+FROM+gas_data").results[0].series[0].values[0][1]
Write-Host "Data points: $count (need >= 20)"
```

Nếu < 20 → Đợi thêm hoặc import flow test

#### Test API manually

```powershell
Invoke-RestMethod -Uri http://localhost:8000/predict `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"MQ135": 234.5, "MQ5": 123.4}'
```

---

## 🚀 Quick Fix: Start from Scratch

Nếu mọi thứ đều bị lỗi, làm lại từ đầu:

### Step 1: Reset Containers

```powershell
# Stop all
docker compose down

# Remove volumes (xóa data cũ)
docker compose down -v

# Start fresh
docker compose up -d

# Wait 30 seconds
Start-Sleep -Seconds 30
```

### Step 2: Verify Services

```powershell
docker compose ps
# All should be "Up"
```

### Step 3: Setup InfluxDB (Manual)

```powershell
# Create database
Invoke-RestMethod -Uri "http://localhost:8086/query" -Method Post -Body "q=CREATE+DATABASE+gasdb"

# Verify
Invoke-RestMethod -Uri "http://localhost:8086/query?q=SHOW+DATABASES"
```

### Step 4: Import Simple Test Flow

1. Node-RED: http://localhost:1880
2. Menu → Import → `nodered-flow-simple-test.json`
3. Click **Deploy**
4. Đợi 60 giây (để tích lũy data)

### Step 5: Verify Data

```powershell
Invoke-RestMethod -Uri "http://localhost:8086/query?db=gasdb&q=SELECT+COUNT(*)+FROM+gas_data"
# Should return count > 10
```

### Step 6: Setup Grafana Data Source

1. Grafana: http://localhost:3000 (admin/admin)
2. **Connections** → **Data sources** → **Add new data source**
3. Chọn **InfluxDB**
4. Config:
```
Query Language: InfluxQL
URL: http://influxdb:8086
Database: gasdb
HTTP Method: GET
```
5. **Save & Test** → ✅ Success

### Step 7: Import Simple Dashboard

1. **Dashboards** → **New** → **Import**
2. Upload `grafana-dashboard-simple-test.json`
3. Select InfluxDB data source
4. Click **Import**

### Step 8: View Dashboard

Dashboard phải hiển thị:
- ✅ Time series chart với 2 lines (MQ135, MQ5)
- ✅ 2 Gauge panels
- ✅ ML Predictions chart (nếu API đang chạy)

---

## 📊 Expected Behavior

### Sau 2 phút chạy flow:

**InfluxDB:**
```
gas_data: ~24 data points (5s interval × 2 min)
gas_predictions: ~12 points (10s interval × 2 min)
```

**Grafana:**
- Chart có data từ 2 phút trước đến giờ
- Gauges hiển thị giá trị cuối cùng
- Auto-refresh 5s

**Node-RED Debug:**
```
msg.payload: [{"measurement": "gas_data", "fields": {...}}]
MQ135: 234, MQ5: 123
```

---

## 🆘 Still Not Working?

### Check Docker Logs

```powershell
# InfluxDB logs
docker logs influxdb --tail 50

# Node-RED logs
docker logs nodered --tail 50

# Grafana logs
docker logs grafana --tail 50
```

### Check Ports

```powershell
# Make sure ports are not in use
netstat -ano | findstr ":1880"  # Node-RED
netstat -ano | findstr ":3000"  # Grafana
netstat -ano | findstr ":8086"  # InfluxDB
netstat -ano | findstr ":8000"  # FastAPI
```

### Restart Everything

```powershell
docker compose restart
Start-Sleep -Seconds 30
docker compose ps
```

### Check Firewall

Windows Firewall có thể block Docker:

```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "Docker InfluxDB" -Direction Inbound -LocalPort 8086 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Docker Grafana" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Docker NodeRED" -Direction Inbound -LocalPort 1880 -Protocol TCP -Action Allow
```

---

## 📝 Summary

**Top 3 lỗi phổ biến:**

1. ❌ Data source URL sai: `localhost` → ✅ Dùng `influxdb`
2. ❌ Flow chưa Deploy → ✅ Click nút Deploy
3. ❌ Time range sai → ✅ Chọn "Last 15 minutes"

**Quick test command:**
```powershell
# All-in-one verification
docker compose ps; `
Invoke-RestMethod "http://localhost:8086/query?db=gasdb&q=SELECT+COUNT(*)+FROM+gas_data"; `
Invoke-RestMethod "http://localhost:8000/health"
```

Nếu vẫn không được, screenshot các lỗi và tôi sẽ giúp debug cụ thể! 🔧
