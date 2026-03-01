# 🔥 Gas Monitoring System

Smart gas monitoring system with real-time ML predictions and Telegram alerts.

## 🚀 Quick Start

```powershell
# 1. Start Docker services
docker-compose up -d

# 2. Start ML API
python ml_predictor_hybrid.py

# 3. Access services
# Node-RED: http://localhost:1880
# Grafana: http://localhost:3000 (admin/admin)
# API: http://localhost:8000
```

## 📦 Tech Stack

| Service | Port | Description |
|---------|------|-------------|
| **Node-RED** | 1880 | Data collection & flow control |
| **InfluxDB 1.8** | 8086 | Time-series database |
| **Grafana** | 3000 | Visualization dashboard |
| **FastAPI** | 8000 | ML API (LSTM + SVM) |
| **Telegram Bot** | - | Real-time alerts |

## 🧠 ML Models

### LSTM Regression (3 models)
- **CO**: `lstm_co_model.h5` (20×17 features)
- **Ethanol**: `lstm_eth_model_gen.h5` (20×17 features)
- **Temperature**: `lstm_ht_model.h5` (20×9 features)

### SVM Classification
- **Status**: `svm_ht_model_downsampled_10x.pkl`
- **Classes**: NORMAL, WARNING, DANGER
- **Scaler**: `ht_sensor_scaler.pkl`

## 🚨 Alert Logic

| Condition | Level | Action |
|-----------|-------|--------|
| CO > 0.7 OR Temp > 0.8 OR SVM=DANGER | 🚨 DANGER | Telegram |
| CO > 0.5 OR Ethanol > 0.6 OR SVM=WARNING | ⚠️ WARNING | Telegram |
| All OK AND SVM=NORMAL | ✅ NORMAL | None |

## 📁 Project Structure

```
gas-dashboard/
├── ml_predictor_hybrid.py          # FastAPI ML server
├── docker-compose.yml              # Docker services
├── requirements.txt                # Python dependencies
├── nodered-flow-ml-api.json        # Main Node-RED flow
├── nodered-flow-telegram.json      # Telegram integration
├── grafana-dashboard-enhanced-direct.json  # Dashboard config
├── lstm_*.h5                       # LSTM models
├── svm_*.pkl, *_scaler.pkl         # SVM model + scaler
├── SETUP-GUIDE.md                  # Detailed setup
├── DEVELOPER.md                    # Architecture docs
└── TROUBLESHOOTING.md              # Common issues
```

## 🔄 Data Flow

```
Sensors → Node-RED → InfluxDB (gas_data)
                          ↓
                    ML API (FastAPI)
                    ├─ 3 LSTM → Predictions
                    └─ 1 SVM → Classification
                          ↓
            InfluxDB (gas_predictions) + Telegram
                          ↓
                   Grafana Dashboard
```

## ⚙️ Installation

### Prerequisites
- Docker Desktop
- Python 3.10+
- 4GB RAM minimum

### Setup

**1. Clone repository**
```bash
git clone https://github.com/yourusername/gas-dashboard.git
cd gas-dashboard
```

**2. Install Python dependencies**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**3. Start services**
```powershell
docker-compose up -d
python ml_predictor_hybrid.py
```

**4. Import configurations**
- **Node-RED**: Import `nodered-flow-ml-api.json` at http://localhost:1880
- **Grafana**: Import `grafana-dashboard-enhanced-direct.json` at http://localhost:3000

See [SETUP-GUIDE.md](SETUP-GUIDE.md) for detailed instructions.

## 📱 Telegram Integration (Optional)

1. Create bot via [@BotFather](https://t.me/BotFather)
2. Get Chat ID from [@getidsbot](https://t.me/getidsbot)
3. Import `nodered-flow-telegram.json` in Node-RED
4. Configure bot token and chat ID
5. Deploy

## 🔍 API Endpoints

```bash
# Health check
GET http://localhost:8000/health

# Model info
GET http://localhost:8000/models

# Predict
POST http://localhost:8000/predict
Content-Type: application/json

{
  "MQ135": 250.5,
  "MQ5": 150.3,
  "R1": 100.0,
  "R2": 110.5,
  ...
}
```

**Response:**
```json
{
  "co": 0.42,
  "ethanol": 0.35,
  "temperature": 0.68,
  "svm_classification": {
    "class": "WARNING",
    "confidence": 0.87
  },
  "alert_level": "WARNING",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 🛠️ Development

```powershell
# Run with auto-reload
uvicorn ml_predictor_hybrid:app --reload

# Check logs
docker logs nodered
docker logs influxdb
docker logs grafana
```

## 🆘 Troubleshooting

**API not starting:**
```powershell
pip install -r requirements.txt --upgrade
python ml_predictor_hybrid.py
```

**No data in Grafana:**
- Wait 3-4 minutes for data collection
- Check InfluxDB: `curl http://localhost:8086/query?db=gasdb&q=SHOW+MEASUREMENTS`
- Verify Node-RED flow is deployed

**Docker issues:**
```powershell
docker-compose down
docker-compose up -d
```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more solutions.

## 📚 Documentation

- **[SETUP-GUIDE.md](SETUP-GUIDE.md)** - Complete installation guide
- **[DEVELOPER.md](DEVELOPER.md)** - Architecture and API details
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and fixes

## 🎯 Features

✅ Hybrid ML: LSTM regression + SVM classification  
✅ Real-time predictions (every 10s)  
✅ Multi-tier alerts (NORMAL/WARNING/DANGER)  
✅ Interactive Grafana dashboard  
✅ Telegram notifications  
✅ Docker containerized  
✅ FastAPI with auto-reload  

## 📄 License

MIT License

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first.

---

**Made with ❤️ for IoT monitoring**
