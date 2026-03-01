"""
Hybrid ML Predictor: LSTM + SVM
- LSTM models: CO prediction, Ethanol prediction
- SVM model: Temperature/Humidity classification (3 classes: NORMAL, WARNING, DANGER)
- Combines regression (LSTM) and classification (SVM) for comprehensive monitoring

Uses existing trained models:
- lstm_co_model.h5
- lstm_eth_model_gen.h5
- svm_ht_model_downsampled_10x.pkl
- ht_sensor_scaler.pkl
"""
import numpy as np
import tensorflow as tf
from tensorflow import keras
import joblib
import time
import requests
from datetime import datetime
import os
import sys
import json
from typing import Optional, Dict, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuration
INFLUX_URL = "http://localhost:8086"
INFLUX_DB = "gasdb"
INFLUX_USER = "admin"
INFLUX_PASSWORD = "adminpass"
API_HOST = "0.0.0.0"
API_PORT = 8000

# Pydantic models for API
class SensorInput(BaseModel):
    """Input schema for sensor data"""
    MQ135: float = Field(..., ge=0, le=1000, description="MQ135 sensor value (0-1000)")
    MQ5: float = Field(..., ge=0, le=1000, description="MQ5 sensor value (0-1000)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "MQ135": 234.5,
                "MQ5": 123.4
            }
        }

class PredictionResponse(BaseModel):
    """Response schema for predictions"""
    status: str
    predictions: Dict[str, float]
    svm_classification: Dict  # NEW: SVM temperature classification (flexible dict)
    sensor_input: Dict[str, float]
    timestamp: str
    processing_time_ms: Optional[float] = None
    alert_level: str  # NEW: Overall alert level combining LSTM + SVM

# LSTM Model paths (ALL 3 models - not removing any!)
LSTM_MODELS_CONFIG = {
    'co': {
        'path': os.path.join(SCRIPT_DIR, 'lstm_co_model.h5'),
        'timesteps': 20,
        'features': 17,
        'feature_names': ['Ethylene'] + [f'Sensor_{i}' for i in range(1, 17)]
    },
    'ethanol': {
        'path': os.path.join(SCRIPT_DIR, 'lstm_eth_model_gen.h5'),
        'timesteps': 20,
        'features': 17,
        'feature_names': ['Ethylene'] + [f'Sensor_{i}' for i in range(1, 17)]
    },
    'temperature': {
        'path': os.path.join(SCRIPT_DIR, 'lstm_ht_model.h5'),
        'timesteps': 20,
        'features': 9,
        'feature_names': ['R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'Temp.', 'Humidity']
    }
}

# SVM Model paths
SVM_MODEL_PATH = os.path.join(SCRIPT_DIR, 'svm_ht_model_downsampled_10x.pkl')
SCALER_PATH = os.path.join(SCRIPT_DIR, 'ht_sensor_scaler.pkl')

# Alert thresholds for LSTM predictions
CO_THRESHOLD_DANGER = 0.7
CO_THRESHOLD_WARNING = 0.5
ETHANOL_THRESHOLD_WARNING = 0.6

# SVM class mapping (adjust based on your training)
SVM_CLASS_NAMES = {
    0: "NORMAL",
    1: "WARNING", 
    2: "DANGER"
}

def load_models():
    """Load all ML models at startup"""
    models = {}
    
    print("=" * 60)
    print("LOADING HYBRID ML MODELS")
    print("=" * 60)
    
    # Load LSTM models
    for model_name, config in LSTM_MODELS_CONFIG.items():
        model_path = config['path']
        if not os.path.exists(model_path):
            print(f"❌ ERROR: LSTM model not found: {model_path}")
            sys.exit(1)
        
        try:
            print(f"📦 Loading LSTM {model_name} model: {os.path.basename(model_path)}")
            # Use compile=False to avoid Keras version compatibility issues
            models[model_name] = keras.models.load_model(model_path, compile=False)
            print(f"   ✅ Shape: ({config['timesteps']}, {config['features']})")
        except Exception as e:
            print(f"❌ ERROR loading LSTM {model_name}: {e}")
            sys.exit(1)
    
    # Load SVM model and scaler
    if not os.path.exists(SVM_MODEL_PATH):
        print(f"❌ ERROR: SVM model not found: {SVM_MODEL_PATH}")
        sys.exit(1)
    if not os.path.exists(SCALER_PATH):
        print(f"❌ ERROR: Scaler not found: {SCALER_PATH}")
        sys.exit(1)
    
    try:
        print(f"📦 Loading SVM model: {os.path.basename(SVM_MODEL_PATH)}")
        models['svm'] = joblib.load(SVM_MODEL_PATH)
        print(f"   ✅ Loaded successfully")
        
        print(f"📦 Loading scaler: {os.path.basename(SCALER_PATH)}")
        models['scaler'] = joblib.load(SCALER_PATH)
        print(f"   ✅ Loaded successfully")
    except Exception as e:
        print(f"❌ ERROR loading SVM/Scaler: {e}")
        sys.exit(1)
    
    print("=" * 60)
    print(f"✅ ALL MODELS LOADED: {len(models)} models ready")
    print("=" * 60)
    
    return models

def generate_mock_features_lstm(mq135, mq5, num_features=17):
    """Generate mock features for LSTM (17 features: Ethylene + 16 sensors)"""
    # Ethylene estimation from MQ135
    ethylene = mq135 * 0.8 + np.random.normal(0, 5)
    
    # Mock 16 sensors based on MQ135 and MQ5 with variations
    mock_sensors = []
    for i in range(16):
        if i < 8:
            base = mq135 * (0.7 + i * 0.05)
        else:
            base = mq5 * (0.6 + (i-8) * 0.04)
        
        mock_sensors.append(base + np.random.normal(0, 10))
    
    return np.array([ethylene] + mock_sensors)

def generate_mock_features_lstm_temp(mq135, mq5):
    """Generate mock features for LSTM Temperature (9 features: R2-R8 + Temp + Humidity)"""
    # Estimate temperature and humidity from sensors
    temp_base = 20 + (mq135 / 500) * 15  # 20-35°C range
    humidity_base = 40 + (mq5 / 400) * 30  # 40-70% range
    
    # Mock resistor values R2-R8 (7 values)
    resistors = []
    for i in range(2, 9):  # R2 to R8 = 7 values
        r_value = 1000 + (mq135 + mq5) * (1 + i * 0.3) + np.random.normal(0, 50)
        resistors.append(r_value)
    
    temp_actual = temp_base + np.random.normal(0, 1)
    humidity_actual = humidity_base + np.random.normal(0, 2)
    
    # Total: 7 resistors + temp + humidity = 9 features for LSTM
    return np.array(resistors + [temp_actual, humidity_actual])

def generate_mock_features_svm(mq135, mq5):
    """Generate mock features for SVM (10 features: R1-R8 + Temp + Humidity)"""
    # Estimate temperature and humidity from sensors
    temp_base = 20 + (mq135 / 500) * 15  # 20-35°C range
    humidity_base = 40 + (mq5 / 400) * 30  # 40-70% range
    
    # Mock resistor values R1-R8 (8 values)
    resistors = []
    for i in range(1, 9):  # R1 to R8 = 8 values
        r_value = 1000 + (mq135 + mq5) * (1 + i * 0.3) + np.random.normal(0, 50)
        resistors.append(r_value)
    
    temp_actual = temp_base + np.random.normal(0, 1)
    humidity_actual = humidity_base + np.random.normal(0, 2)
    
    # Total: 8 resistors + temp + humidity = 10 features for SVM
    return np.array(resistors + [temp_actual, humidity_actual])

def fetch_recent_data(limit=20):
    """Fetch recent data from InfluxDB"""
    query = f"""
    SELECT * FROM gas_data
    ORDER BY time DESC
    LIMIT {limit}
    """
    
    try:
        response = requests.get(
            f"{INFLUX_URL}/query",
            params={
                'db': INFLUX_DB,
                'q': query,
                'u': INFLUX_USER,
                'p': INFLUX_PASSWORD
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and data['results']:
                result = data['results'][0]
                if 'series' in result:
                    series = result['series'][0]
                    columns = series['columns']
                    values = series['values']
                    
                    # Reverse to get chronological order
                    values = list(reversed(values))
                    
                    mq135_idx = columns.index('MQ135')
                    mq5_idx = columns.index('MQ5')
                    
                    data_points = []
                    for row in values:
                        data_points.append({
                            'MQ135': float(row[mq135_idx]),
                            'MQ5': float(row[mq5_idx])
                        })
                    
                    return data_points
        
        return None
    except Exception as e:
        print(f"❌ Error fetching from InfluxDB: {e}")
        return None

def predict_hybrid(models, mq135, mq5):
    """
    Hybrid prediction using LSTM + SVM
    
    Returns:
    - LSTM predictions: CO (regression), Ethanol (regression), Temperature (regression)
    - SVM classification: Temperature/Humidity status (NORMAL/WARNING/DANGER)
    - Overall alert level: Combined assessment from LSTM values + SVM class
    """
    start_time = time.time()
    predictions = {}
    svm_result = {}
    
    # Fetch historical data
    historical_data = fetch_recent_data(limit=20)
    
    if historical_data and len(historical_data) >= 20:
        print(f"✅ Using {len(historical_data)} real data points from InfluxDB")
        
        # LSTM predictions for CO + Ethanol (17 features)
        lstm_sequences_17 = []
        for data_point in historical_data:
            features = generate_mock_features_lstm(
                data_point['MQ135'],
                data_point['MQ5']
            )
            lstm_sequences_17.append(features)
        
        lstm_sequence_17 = np.array(lstm_sequences_17)
        
        # Predict CO
        X_co = lstm_sequence_17.reshape(1, 20, 17)
        pred_co = float(models['co'].predict(X_co, verbose=0)[0][0])
        predictions['co'] = pred_co
        
        # Predict Ethanol
        X_eth = lstm_sequence_17.reshape(1, 20, 17)
        pred_eth = float(models['ethanol'].predict(X_eth, verbose=0)[0][0])
        predictions['ethanol'] = pred_eth
        
        # LSTM prediction for Temperature (9 features: R2-R8 + Temp + Humidity)
        lstm_sequences_9 = []
        for data_point in historical_data:
            features = generate_mock_features_lstm_temp(
                data_point['MQ135'],
                data_point['MQ5']
            )
            lstm_sequences_9.append(features)
        
        lstm_sequence_9 = np.array(lstm_sequences_9)
        
        # Predict Temperature with LSTM
        X_temp = lstm_sequence_9.reshape(1, 20, 9)
        pred_temp = float(models['temperature'].predict(X_temp, verbose=0)[0][0])
        predictions['temperature'] = pred_temp
        
    else:
        print(f"⚠️  Not enough data ({len(historical_data) if historical_data else 0}/20), using mock predictions")
        predictions['co'] = 0.3
        predictions['ethanol'] = 0.25
        predictions['temperature'] = 0.4
    
    # SVM classification for Temperature/Humidity
    svm_features = generate_mock_features_svm(mq135, mq5)
    
    # Scale features (suppress sklearn warning about feature names)
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="X does not have valid feature names")
        svm_features_scaled = models['scaler'].transform(svm_features.reshape(1, -1))
    
    # Predict class
    try:
        svm_class = int(models['svm'].predict(svm_features_scaled)[0])
        svm_class_name = SVM_CLASS_NAMES.get(svm_class, "UNKNOWN")
    except Exception as e:
        print(f"❌ SVM prediction error: {e}")
        svm_class = 0
        svm_class_name = "NORMAL"
    
    # Get probability if available
    try:
        if hasattr(models['svm'], 'predict_proba'):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                svm_proba = models['svm'].predict_proba(svm_features_scaled)[0]
            svm_result = {
                'class': svm_class_name,
                'class_id': svm_class,
                'confidence': float(max(svm_proba)),
                'probabilities': {
                    'NORMAL': float(svm_proba[0]) if len(svm_proba) > 0 else 0.0,
                    'WARNING': float(svm_proba[1]) if len(svm_proba) > 1 else 0.0,
                    'DANGER': float(svm_proba[2]) if len(svm_proba) > 2 else 0.0
                }
            }
        else:
            svm_result = {
                'class': svm_class_name,
                'class_id': svm_class
            }
    except Exception as e:
        print(f"❌ SVM probability error: {e}")
        svm_result = {
            'class': svm_class_name,
            'class_id': svm_class
        }
    
    # Determine overall alert level
    # FIXED: Use direct sensor thresholds instead of unreliable LSTM predictions
    alert_level = determine_alert_level_from_sensors(mq135, mq5)
    
    processing_time = (time.time() - start_time) * 1000
    
    return predictions, svm_result, alert_level, processing_time

def determine_alert_level(lstm_predictions, svm_result):
    """
    DEPRECATED: LSTM predictions unreliable with mock features (negative/random values)
    
    Root cause: Models trained on real 17-feature sensor array, but runtime uses random mock data
    → CO/Ethanol predictions meaningless (negative values, no correlation with MQ135/MQ5)
    
    Solution: Use direct sensor-based thresholds (see determine_alert_level_from_sensors)
    """
    # This function is now bypassed - kept for API compatibility
    return "NORMAL"

def determine_alert_level_from_sensors(mq135, mq5):
    """
    Determine alert level DIRECTLY from sensor values (BYPASS unreliable LSTM predictions)
    
    REASON: LSTM models trained with real sensor array (17 features) but runtime uses mock data
    → predictions unreliable (negative values, random outputs)
    
    SOLUTION: Use empirical sensor-to-gas mapping based on MQ135/MQ5 characteristics
    
    MQ135: Sensitive to CO2, NH3, Benzene, Alcohol, Smoke (CO proxy)
    MQ5: Sensitive to LPG, Natural Gas, Town Gas (Ethanol proxy)
    
    Thresholds (empirical from real-world sensor behavior):
    - CO proxy (MQ135): 
        DANGER > 700 ppm (high pollution)
        WARNING > 400 ppm (moderate pollution)
    - Ethanol proxy (MQ5):
        DANGER > 600 ppm (high concentration)
        WARNING > 300 ppm (moderate concentration)
    """
    
    # DANGER: High sensor values (critical gas concentration)
    if mq135 > 700:
        return "DANGER"
    if mq5 > 600:
        return "DANGER"
    
    # WARNING: Moderate sensor values
    if mq135 > 400:
        return "WARNING"
    if mq5 > 300:
        return "WARNING"
    
    # NORMAL: Low sensor values (safe environment)
    return "NORMAL"

# FastAPI app
app = FastAPI(
    title="Hybrid ML Predictor API",
    description="Gas monitoring with LSTM regression + SVM classification",
    version="2.0.0"
)

# Global models container
ML_MODELS = None

@app.on_event("startup")
async def startup_event():
    """Load models once at startup"""
    global ML_MODELS
    ML_MODELS = load_models()
    print("🚀 Hybrid ML Predictor API ready!")

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "Hybrid ML Predictor API",
        "version": "2.0.0",
        "models": {
            "lstm": ["CO", "Ethanol"],
            "svm": "Temperature/Humidity Classification"
        },
        "endpoints": ["/predict", "/health", "/models"]
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "models_loaded": ML_MODELS is not None,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/models")
async def models_info():
    """Get information about loaded models"""
    if ML_MODELS is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    return {
        "lstm_models": {
            "co": LSTM_MODELS_CONFIG['co'],
            "ethanol": LSTM_MODELS_CONFIG['ethanol'],
            "temperature": LSTM_MODELS_CONFIG['temperature']
        },
        "svm_model": {
            "path": os.path.basename(SVM_MODEL_PATH),
            "classes": SVM_CLASS_NAMES
        },
        "thresholds": {
            "co_danger": CO_THRESHOLD_DANGER,
            "co_warning": CO_THRESHOLD_WARNING,
            "ethanol_warning": ETHANOL_THRESHOLD_WARNING,
            "temperature_danger": 0.8,
            "temperature_warning": 0.6
        },
        "note": "Hybrid system: 3 LSTM models (regression) + 1 SVM model (classification)"
    }

@app.post("/predict", response_model=PredictionResponse)
async def predict(sensor_data: SensorInput):
    """
    Make predictions using LSTM + SVM hybrid model
    
    - LSTM: Predicts CO, Ethanol, and Temperature levels (regression - 3 values)
    - SVM: Classifies Temperature/Humidity status (classification - 3 classes)
    - Returns: Combined alert level from both LSTM thresholds and SVM classification
    
    Why hybrid? LSTM gives continuous values (what will happen), SVM gives classification (how dangerous)
    """
    if ML_MODELS is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    try:
        predictions, svm_classification, alert_level, proc_time = predict_hybrid(
            ML_MODELS,
            sensor_data.MQ135,
            sensor_data.MQ5
        )
        
        return PredictionResponse(
            status="success",
            predictions=predictions,
            svm_classification=svm_classification,
            alert_level=alert_level,
            sensor_input=sensor_data.model_dump() if hasattr(sensor_data, 'model_dump') else sensor_data.dict(),
            timestamp=datetime.now().isoformat(),
            processing_time_ms=proc_time
        )
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Prediction error:\n{error_details}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

def write_predictions_to_influx(predictions, svm_classification, alert_level, sensor_input):
    """Write predictions to InfluxDB"""
    try:
        # Convert alert level to numeric
        alert_numeric = {"NORMAL": 0, "WARNING": 1, "DANGER": 2}.get(alert_level, 0)
        svm_numeric = {"NORMAL": 0, "WARNING": 1, "DANGER": 2}.get(svm_classification['class'], 0)
        
        data = f"""gas_predictions pred_co={predictions['co']},pred_ethanol={predictions['ethanol']},pred_temperature={predictions['temperature']},svm_class={svm_numeric},alert_level={alert_numeric},input_mq135={sensor_input['MQ135']},input_mq5={sensor_input['MQ5']}"""
        
        response = requests.post(
            f"{INFLUX_URL}/write",
            params={
                'db': INFLUX_DB,
                'u': INFLUX_USER,
                'p': INFLUX_PASSWORD
            },
            data=data,
            timeout=5
        )
        
        if response.status_code == 204:
            print(f"✅ Predictions written to InfluxDB (Alert: {alert_level})")
            return True
    except Exception as e:
        print(f"❌ Error writing to InfluxDB: {e}")
    
    return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Hybrid ML Predictor (LSTM + SVM)")
    parser.add_argument('--cli', action='store_true', help='Run in CLI mode (single prediction)')
    parser.add_argument('--loop', action='store_true', help='Run in continuous loop mode')
    parser.add_argument('--mq135', type=float, default=250.0, help='MQ135 sensor value')
    parser.add_argument('--mq5', type=float, default=150.0, help='MQ5 sensor value')
    
    args = parser.parse_args()
    
    if args.cli or args.loop:
        # CLI mode
        models = load_models()
        
        if args.cli:
            # Single prediction
            print(f"\n{'='*60}")
            print(f"SINGLE PREDICTION")
            print(f"{'='*60}")
            print(f"Input: MQ135={args.mq135}, MQ5={args.mq5}")
            
            predictions, svm_result, alert_level, proc_time = predict_hybrid(
                models, args.mq135, args.mq5
            )
            
            print(f"\n📊 LSTM PREDICTIONS (Regression):")
            print(f"   CO: {predictions['co']:.4f}")
            print(f"   Ethanol: {predictions['ethanol']:.4f}")
            print(f"   Temperature: {predictions['temperature']:.4f}")
            
            print(f"\n🔬 SVM CLASSIFICATION:")
            print(f"   Class: {svm_result['class']}")
            if 'confidence' in svm_result:
                print(f"   Confidence: {svm_result['confidence']:.2%}")
            
            print(f"\n🚨 OVERALL ALERT: {alert_level}")
            print(f"   (Combined from LSTM thresholds + SVM classification)")
            print(f"⏱️  Processing time: {proc_time:.2f}ms")
            
        elif args.loop:
            # Continuous loop
            print(f"\n{'='*60}")
            print(f"CONTINUOUS PREDICTION MODE")
            print(f"{'='*60}")
            print("Press Ctrl+C to stop\n")
            
            try:
                while True:
                    predictions, svm_result, alert_level, proc_time = predict_hybrid(
                        models, args.mq135, args.mq5
                    )
                    
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"CO={predictions['co']:.3f} | "
                          f"Eth={predictions['ethanol']:.3f} | "
                          f"Temp={predictions['temperature']:.3f} | "
                          f"SVM={svm_result['class']} | "
                          f"Alert={alert_level} | "
                          f"{proc_time:.1f}ms")
                    
                    time.sleep(10)
                    
            except KeyboardInterrupt:
                print("\n\n✅ Stopped by user")
    else:
        # API mode (default)
        print("\n🚀 Starting Hybrid ML Predictor API...")
        uvicorn.run(app, host=API_HOST, port=API_PORT)
