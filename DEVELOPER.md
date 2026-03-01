# 📚 Developer Guide - Gas Monitoring System

Hướng dẫn chi tiết về kiến trúc, models, và development cho developers.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Gas Monitoring System                    │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐
│ Sensors      │ MQ135, MQ5 (simulated every 10s)
└──────┬───────┘
       │
       v
┌──────────────┐
│ Node-RED     │ Data collection + Flow control
│ (Port 1880)  │
└──────┬───────┘
       │
       ├──→ ┌──────────────┐
       │    │  InfluxDB    │ Time-series storage (gas_data)
       │    │ (Port 8086)  │
       │    └──────────────┘
       │
       v
┌──────────────┐
│  ML API      │ LSTM + SVM predictions
│ (Port 8000)  │
└──────┬───────┘
       │
       ├──→ InfluxDB (gas_predictions)
       │
       ├──→ Telegram (alerts)
       │
       └──→ Grafana (Port 3000) - Visualization
```

---

## 🧠 Machine Learning Models

### Model 1: LSTM CO Prediction

**File:** `lstm_co_model.h5`

**Architecture:**
```python
Input: (20, 17) # 20 timesteps × 17 features
└─ LSTM(64 units, return_sequences=True)
   └─ Dropout(0.2)
      └─ LSTM(32 units)
         └─ Dense(16, activation='relu')
            └─ Dense(1, activation='sigmoid')  # CO output [0-1]
```

**Features (17):**
- Ethylene concentration
- R1-R8 resistance (8 sensors)
- Temperature
- Humidity
- Previous CO value (t-1)
- Rolling mean CO (3 timesteps)
- Rolling std CO (3 timesteps)
- Delta CO (t - t-1)
- Delta rolling mean (t - t-1)
- Delta rolling std (t - t-1)

**Training:**
```bash
python train_lstm_co.py
```

---

### Model 2: LSTM Ethanol Prediction

**File:** `lstm_eth_model_gen.h5`

**Architecture:**
```python
Input: (20, 17) # Same as CO
└─ LSTM(64 units, return_sequences=True)
   └─ Dropout(0.2)
      └─ LSTM(32 units)
         └─ Dense(16, activation='relu')
            └─ Dense(1, activation='sigmoid')  # Ethanol output [0-1]
```

**Features (17):**
- Same as CO model (shared feature engineering)

**Training:**
```bash
python train_lstm_eth_generator.py
```

---

### Model 3: LSTM Temperature Prediction

**File:** `lstm_ht_model.h5`

**Architecture:**
```python
Input: (20, 9) # 20 timesteps × 9 features
└─ LSTM(64 units, return_sequences=True)
   └─ Dropout(0.2)
      └─ LSTM(32 units)
         └─ Dense(16, activation='relu')
            └─ Dense(1, activation='sigmoid')  # Temperature output [0-1]
```

**Features (9):**
- R2-R8 resistance (7 sensors)
- Temperature (current)
- Humidity (current)

**Training:**
```bash
# Train from create_lstm_sequences.py
python create_lstm_sequences.py
```

---

### Model 4: SVM Classification (Hybrid Mode Only)

**File:** `svm_ht_model_downsampled_10x.pkl`
**Scaler:** `ht_sensor_scaler.pkl`

**Architecture:**
```python
# Support Vector Machine
SVM(kernel='rbf', C=1.0, gamma='scale')
```

**Features (10):**
- R1-R8 resistance (8 sensors) - ⚠️ Includes R1 (different from LSTM temp)
- Temperature
- Humidity

**Output Classes:**
- `NORMAL` (0): Safe conditions
- `WARNING` (1): Elevated risk
- `DANGER` (2): Critical levels

**Training:**
```bash
# Use existing trained model
# Or retrain with new data:
python train_svm_ht.py
```

**Feature Scaling:**
```python
# MinMaxScaler fitted on training data
scaler = joblib.load('ht_sensor_scaler.pkl')
X_scaled = scaler.transform(X_raw)
```

---

## 📦 Feature Engineering

### LSTM Features (17 for CO/Ethanol)

```python
def generate_mock_features_lstm(base_ethylene, resistances):
    """
    Creates 17 features for CO/Ethanol LSTM models.
    
    Args:
        base_ethylene: Ethylene concentration
        resistances: Dict with R1-R8 values
    
    Returns:
        np.array of shape (20, 17)
    """
    features = []
    for t in range(20):
        timestep_features = [
            base_ethylene + np.random.normal(0, 0.01),  # Ethylene
            *[resistances[f'R{i}'] + np.random.normal(0, 5) for i in range(1, 9)],  # R1-R8
            25 + np.random.uniform(-2, 2),  # Temperature
            60 + np.random.uniform(-5, 5),  # Humidity
            0.3 + np.random.uniform(-0.1, 0.1),  # Previous CO
            0.32 + np.random.uniform(-0.05, 0.05),  # Rolling mean CO
            0.05 + np.random.uniform(0, 0.02),  # Rolling std CO
            np.random.uniform(-0.02, 0.02),  # Delta CO
            np.random.uniform(-0.01, 0.01),  # Delta rolling mean
            np.random.uniform(-0.005, 0.005),  # Delta rolling std
        ]
        features.append(timestep_features)
    
    return np.array(features).reshape(1, 20, 17)
```

### LSTM Features (9 for Temperature)

```python
def generate_mock_features_lstm_temp():
    """
    Creates 9 features for Temperature LSTM model.
    ⚠️ NOTE: Uses R2-R8 only (7 sensors), not R1
    
    Returns:
        np.array of shape (20, 9)
    """
    features = []
    for t in range(20):
        timestep_features = [
            *[100 + np.random.uniform(-20, 20) for _ in range(7)],  # R2-R8
            25 + np.random.uniform(-2, 2),  # Temperature
            60 + np.random.uniform(-5, 5),  # Humidity
        ]
        features.append(timestep_features)
    
    return np.array(features).reshape(1, 20, 9)
```

### SVM Features (10)

```python
def generate_mock_features_svm():
    """
    Creates 10 features for SVM classification.
    ⚠️ NOTE: Uses R1-R8 (8 sensors), includes R1
    
    Returns:
        np.array of shape (1, 10)
    """
    features = [
        *[100 + np.random.uniform(-20, 20) for _ in range(8)],  # R1-R8
        25 + np.random.uniform(-2, 2),  # Temperature
        60 + np.random.uniform(-5, 5),  # Humidity
    ]
    
    return np.array(features).reshape(1, 10)
```

---

## 🔄 Prediction Pipeline

### LSTM Only Mode

```python
# ml_predictor_mocked.py
@app.post("/predict")
async def predict(request: SensorDataRequest):
    # 1. Generate features
    features_co_eth = generate_mock_features_lstm(...)  # (1, 20, 17)
    features_temp = generate_mock_features_lstm_temp()  # (1, 20, 9)
    
    # 2. Predict
    co = co_model.predict(features_co_eth)[0][0]
    ethanol = ethanol_model.predict(features_co_eth)[0][0]
    temp = temp_model.predict(features_temp)[0][0]
    
    # 3. Determine alert
    if co > 0.7:
        alert = "DANGER"
    elif co > 0.5 or ethanol > 0.6:
        alert = "WARNING"
    else:
        alert = "NORMAL"
    
    return {"co": co, "ethanol": ethanol, "temperature": temp, "alert_level": alert}
```

### Hybrid Mode (LSTM + SVM)

```python
# ml_predictor_hybrid.py
@app.post("/predict")
async def predict_hybrid(request: SensorDataRequest):
    # 1. LSTM Predictions
    features_co_eth = generate_mock_features_lstm(...)
    features_temp = generate_mock_features_lstm_temp()
    
    co = co_model.predict(features_co_eth)[0][0]
    ethanol = ethanol_model.predict(features_co_eth)[0][0]
    temp = temp_model.predict(features_temp)[0][0]
    
    # 2. SVM Classification
    features_svm = generate_mock_features_svm()  # (1, 10)
    features_scaled = scaler.transform(features_svm)
    
    svm_class_idx = svm_model.predict(features_scaled)[0]
    svm_probabilities = svm_model.predict_proba(features_scaled)[0]
    
    svm_class = ["NORMAL", "WARNING", "DANGER"][svm_class_idx]
    svm_confidence = svm_probabilities[svm_class_idx]
    
    # 3. Combined Alert Logic
    alert = determine_alert_level(co, ethanol, temp, svm_class)
    
    return {
        "co": co,
        "ethanol": ethanol,
        "temperature": temp,
        "svm_classification": {
            "class": svm_class,
            "confidence": svm_confidence,
            "probabilities": {
                "NORMAL": svm_probabilities[0],
                "WARNING": svm_probabilities[1],
                "DANGER": svm_probabilities[2]
            }
        },
        "alert_level": alert
    }
```

### Combined Alert Logic

```python
def determine_alert_level(co, ethanol, temp, svm_class):
    """
    Combines LSTM regression + SVM classification.
    
    Priority:
    1. DANGER if ANY critical threshold OR SVM=DANGER
    2. WARNING if ANY elevated threshold OR SVM=WARNING
    3. NORMAL only if ALL OK AND SVM=NORMAL
    """
    # DANGER conditions
    if co > 0.7 or temp > 0.8 or svm_class == "DANGER":
        return "DANGER"
    
    # WARNING conditions
    if co > 0.5 or ethanol > 0.6 or temp > 0.6 or svm_class == "WARNING":
        return "WARNING"
    
    # NORMAL (all safe)
    return "NORMAL"
```

---

## 🔌 API Endpoints

### GET /

**Response:**
```json
{
  "message": "Gas Monitoring ML Predictor (Hybrid: LSTM + SVM)",
  "status": "running",
  "models": ["CO", "Ethanol", "Temperature", "SVM"]
}
```

### GET /health

**Response:**
```json
{
  "status": "healthy",
  "models_loaded": true,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### GET /models

**Response:**
```json
{
  "co": {
    "input_shape": [20, 17],
    "output_shape": [1],
    "type": "LSTM"
  },
  "ethanol": {
    "input_shape": [20, 17],
    "output_shape": [1],
    "type": "LSTM"
  },
  "temperature": {
    "input_shape": [20, 9],
    "output_shape": [1],
    "type": "LSTM"
  },
  "svm": {
    "n_features": 10,
    "classes": ["NORMAL", "WARNING", "DANGER"],
    "type": "SVM"
  }
}
```

### POST /predict

**Request:**
```json
{
  "MQ135": 250.5,
  "MQ5": 150.3
}
```

**Response (Hybrid):**
```json
{
  "co": 0.42,
  "ethanol": 0.35,
  "temperature": 0.68,
  "svm_classification": {
    "class": "WARNING",
    "confidence": 0.87,
    "probabilities": {
      "NORMAL": 0.05,
      "WARNING": 0.87,
      "DANGER": 0.08
    }
  },
  "alert_level": "WARNING",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 🗄️ Database Schema

### InfluxDB Measurements

**Measurement: `gas_data`**
```
time                MQ135  MQ5    R1   R2   R3   R4   R5   R6   R7   R8   Temp  Humidity
----                -----  ---    --   --   --   --   --   --   --   --   ----  --------
1610712000000000000 250.5  150.3  120  105  98   87   112  93   101  88   25.3  62.1
```

**Tags:** None (time-series only)
**Fields:** MQ135, MQ5, R1-R8, Temp, Humidity (all float64)

**Measurement: `gas_predictions`**
```
time                co    ethanol  temperature  svm_class  svm_confidence  alert_level
----                --    -------  -----------  ---------  --------------  -----------
1610712010000000000 0.42  0.35     0.68         WARNING    0.87            WARNING
```

**Tags:** None
**Fields:** co, ethanol, temperature, svm_confidence (float64), svm_class, alert_level (string)

---

## 📊 Node-RED Flow

### Core Nodes

```javascript
// 1. Inject node (every 10s)
{
  "repeat": "10",
  "crontab": ""
}

// 2. Generate sensor data
msg.payload = {
  MQ135: 200 + Math.random() * 100,
  MQ5: 100 + Math.random() * 100,
  R1: 80 + Math.random() * 40,
  // ... R2-R8
  Temp: 22 + Math.random() * 6,
  Humidity: 55 + Math.random() * 15
};

// 3. Write to InfluxDB (gas_data)
// node-red-contrib-influxdb

// 4. HTTP Request to ML API
{
  "method": "POST",
  "url": "http://host.docker.internal:8000/predict",
  "headers": {"Content-Type": "application/json"}
}

// 5. Process predictions
var predictions = msg.payload;
msg.influx_payload = {
  co: predictions.co,
  ethanol: predictions.ethanol,
  temperature: predictions.temperature,
  svm_class: predictions.svm_classification.class,
  svm_confidence: predictions.svm_classification.confidence,
  alert_level: predictions.alert_level
};

// 6. Write to InfluxDB (gas_predictions)

// 7. Check alert level
if (msg.payload.alert_level === "DANGER" || msg.payload.alert_level === "WARNING") {
  return msg;  // Send to Telegram
}
return null;  // NORMAL, no alert

// 8. Format Telegram message
msg.payload = {
  type: "message",
  chatId: 123456789,
  content: `🚨 ${alert_level} Alert!\n\n` +
           `CO: ${co.toFixed(2)}\n` +
           `Ethanol: ${ethanol.toFixed(2)}\n` +
           `Temperature: ${temp.toFixed(2)}\n\n` +
           `SVM: ${svm_class} (${(confidence*100).toFixed(1)}%)`
};

// 9. Send to Telegram
// node-red-contrib-telegrambot
```

---

## 🧪 Testing

### Unit Tests

```python
# test_ml_predictor.py
import pytest
from ml_predictor_hybrid import generate_mock_features_lstm, generate_mock_features_svm

def test_lstm_feature_shape():
    features = generate_mock_features_lstm(0.5, {f'R{i}': 100 for i in range(1, 9)})
    assert features.shape == (1, 20, 17)

def test_svm_feature_shape():
    features = generate_mock_features_svm()
    assert features.shape == (1, 10)

def test_prediction_range():
    response = client.post("/predict", json={"MQ135": 250, "MQ5": 150})
    data = response.json()
    assert 0 <= data["co"] <= 1
    assert 0 <= data["ethanol"] <= 1
    assert 0 <= data["temperature"] <= 1
```

### Integration Tests

```powershell
# 1. Start services
docker-compose up -d
python ml_predictor_hybrid.py

# 2. Send test data
$body = @{MQ135=250; MQ5=150} | ConvertTo-Json
$response = Invoke-RestMethod http://localhost:8000/predict -Method Post -Body $body -ContentType "application/json"

# 3. Verify response
$response.co | Should -BeOfType Double
$response.alert_level | Should -BeIn @("NORMAL", "WARNING", "DANGER")

# 4. Check InfluxDB
Invoke-RestMethod "http://localhost:8086/query?db=gasdb&q=SELECT * FROM gas_predictions LIMIT 1"

# 5. Test Telegram (manual)
# Node-RED → Click "Test Telegram Alert"
```

---

## 🔧 Development Workflow

### 1. Local Development

```powershell
# Setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run API with auto-reload
uvicorn ml_predictor_hybrid:app --reload --host 0.0.0.0 --port 8000

# Test
pytest tests/
```

### 2. Model Training

```powershell
# Prepare data
python create_lstm_sequences_co.py
python create_lstm_sequences_eth.py
python create_lstm_sequences.py

# Train models
python train_lstm_co.py
python train_lstm_eth_generator.py

# Verify
python inspect_models.py
```

### 3. Docker Build

```yaml
# Add to docker-compose.yml (optional)
ml-api:
  build: .
  ports:
    - "8000:8000"
  volumes:
    - .:/app
  depends_on:
    - influxdb
```

### 4. Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add breakpoints
import pdb; pdb.set_trace()

# Profile performance
import cProfile
cProfile.run('predict_hybrid(request)', 'output.prof')
```

---

## 📝 Code Style

### Python (PEP 8)

```python
# Type hints
def predict_hybrid(request: SensorDataRequest) -> PredictionResponse:
    pass

# Docstrings
def generate_mock_features_lstm(base_ethylene: float, resistances: Dict[str, float]) -> np.ndarray:
    """
    Generate mock LSTM features for CO/Ethanol prediction.
    
    Args:
        base_ethylene: Base ethylene concentration (0-1)
        resistances: Dictionary of R1-R8 resistance values
    
    Returns:
        NumPy array of shape (1, 20, 17)
    """
    pass

# Naming conventions
CO_THRESHOLD_DANGER = 0.7  # Constants: UPPER_SNAKE_CASE
sensor_data = {}  # Variables: snake_case
class SensorDataRequest:  # Classes: PascalCase
    pass
```

---

## 🚀 Performance Optimization

### Model Loading

```python
# ✅ Load once at startup (current)
@app.on_event("startup")
async def load_models():
    global co_model, ethanol_model, temp_model
    co_model = keras.models.load_model('lstm_co_model.h5', compile=False)

# ❌ Don't load on every request
@app.post("/predict")
async def predict(request):
    model = keras.models.load_model('lstm_co_model.h5')  # Slow!
```

### Feature Generation

```python
# ✅ Vectorized NumPy operations
features = np.array([...] for _ in range(20))

# ❌ Python loops
features = []
for i in range(20):
    features.append([...])
```

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_scaler():
    return joblib.load('ht_sensor_scaler.pkl')
```

---

## 📦 Dependencies

### requirements.txt

```
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
tensorflow>=2.12.0
scikit-learn>=1.3.0
joblib>=1.3.0
numpy>=1.24.0
python-multipart>=0.0.6
```

### Docker Images

```yaml
influxdb: influxdb:1.8  # Time-series DB
nodered: nodered/node-red:latest  # Flow engine
grafana: grafana/grafana:latest  # Visualization
```

---

✅ **Ready to develop! Happy coding!**
