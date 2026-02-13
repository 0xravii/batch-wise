"""
Anomaly Detection Service
Handles anomaly detection using Isolation Forest model with enhanced features.
"""
import os
import pandas as pd
import numpy as np
import joblib
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlmodel import Session, select, text
import logging

from app.models.domain import AnomalyDetection
from app.core.database import get_session

# Try to import enhanced feature engineering, fall back to basic if unavailable
try:
    from app.ml.feature_engineering import get_feature_engineer
    USE_ENHANCED_FEATURES = True
except ImportError:
    USE_ENHANCED_FEATURES = False
    logging.warning("Enhanced feature engineering not available, using basic features only")

logger = logging.getLogger(__name__)


class AnomalyDetectionService:
    """Service for detecting anomalies in CSV data using Isolation Forest."""
    
    def __init__(self, model_path: str = None, scaler_path: str = None):
        """Initialize the anomaly detection service."""
        # app/services/anomaly.py -> ../artifacts/model.pkl
        # Go up 1 level to app, then into artifacts
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if model_path is None:
            model_path = os.path.join(base_dir, 'artifacts', 'isolation_model.pkl')
        
        if scaler_path is None:
            scaler_path = os.path.join(base_dir, 'artifacts', 'feature_scaler.pkl')
        
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.model = None
        self.scaler = None
        self._load_model()
    
    def _load_model(self):
        """Load the trained Isolation Forest model and scaler."""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                logger.info(f"Loaded Isolation Forest model from {self.model_path}")
            else:
                logger.warning(f"Model file not found: {self.model_path}")
                self.model = None
            
            if os.path.exists(self.scaler_path):
                self.scaler = joblib.load(self.scaler_path)
                logger.info(f"Loaded feature scaler from {self.scaler_path}")
            else:
                logger.warning(f"Scaler file not found: {self.scaler_path}")
                self.scaler = None
                
        except Exception as e:
            logger.error(f"Error loading model/scaler: {e}")
            self.model = None
            self.scaler = None
    
    def calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate KPI features for anomaly detection.
        Uses enhanced features if available, otherwise falls back to basic 6 features.
        """
        # Use enhanced feature engineering if available
        if USE_ENHANCED_FEATURES:
            try:
                feature_engineer = get_feature_engineer()
                df = feature_engineer.engineer_features(df.copy())
                logger.info(f"Using enhanced features: {len(feature_engineer.get_feature_names())} features")
                return df
            except Exception as e:
                logger.error(f"Error with enhanced features, falling back to basic: {e}")
        
        # Fallback to basic feature calculation
        # Rename columns if needed (handle different naming conventions)
        column_mapping = {
            "Energy Consumption (kWh)": "Energy_kWh",
            "Energy_Consumption__kWh_": "Energy_kWh",
            "energy_consumption__kwh_": "Energy_kWh",
            "OutputWeight_kg": "OutputWeight_kg",
            "outputweight_kg": "OutputWeight_kg",
            "InputWeight_kg": "InputWeight_kg",
            "inputweight_kg": "InputWeight_kg",
            "RoomTemp_C": "RoomTemp_C",
            "roomtemp_c": "RoomTemp_C",
            "RoomTemperature_C": "RoomTemp_C",
            "roomtemperature_c": "RoomTemp_C"
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})
        
        # Calculate KPIs
        # Ensure columns exist before calculation to avoid KeyError
        if "Energy_kWh" in df.columns and "OutputWeight_kg" in df.columns:
            df["Energy_per_kg"] = df["Energy_kWh"] / df["OutputWeight_kg"]
        
        if "InputWeight_kg" in df.columns and "OutputWeight_kg" in df.columns:
            df["Yield_loss_pct"] = (
                (df["InputWeight_kg"] - df["OutputWeight_kg"]) / df["InputWeight_kg"]
            ) * 100
        
        if "Energy_kWh" in df.columns and "OutputWeight_kg" in df.columns and "kg_co2_per_kwh" in df.columns:
             df["CO2_per_kg"] = (
                df["Energy_kWh"] * df["kg_co2_per_kwh"]
            ) / df["OutputWeight_kg"]
        elif "Energy_kWh" in df.columns and "OutputWeight_kg" in df.columns:
             # Default CO2 factor if missing
             CO2_FACTOR = 0.5 
             df["CO2_per_kg"] = (df["Energy_kWh"] * CO2_FACTOR) / df["OutputWeight_kg"]
        
        # Interaction: Energy * Temp
        if "Energy_kWh" in df.columns and "RoomTemp_C" in df.columns:
            df["Energy_x_Temp"] = df["Energy_kWh"] * df["RoomTemp_C"]
        
        # Remove infinite and NaN values
        df = df.replace([np.inf, -np.inf], np.nan)
        
        return df
    
    def determine_severity(self, row: pd.Series) -> str:
        """Determine severity level based on anomaly flag AND thresholds (Hybrid)."""
        # Critical thresholds (HARD RULES)
        energy_rule = row.get("Energy_kWh", 0) > 1500  # Increased from 700 based on data avg ~1070
        efficiency_rule = row.get("Energy_per_kg", 0) > 15 # Increased from 7
        yield_rule = row.get("Yield_loss_pct", 0) > 10 # Increased from 2
        co2_rule = row.get("CO2_per_kg", 0) > 6.0 # Increased from 3.0 based on calculation ~3.7
        
        is_model_anomaly = row.get("anomaly_flag") == -1
        
        if energy_rule or efficiency_rule or yield_rule or co2_rule:
             return "RED"
        elif is_model_anomaly:
             return "AMBER"
        else:
             return "GREEN"

    def detect_and_update(self, table_name: str, db: Session) -> Dict[str, Any]:
        """Detect anomalies and update the source table's anomaly_alert column."""
        if self.model is None:
             logger.warning("Model not loaded. Skipping anomaly detection update.")
             return {"status": "skipped", "reason": "model_not_loaded"}
        
        logger.info(f"Running detect_and_update on table: {table_name}")
        
        # Load data
        try:
            query = f"SELECT * FROM {table_name}"
            result = db.exec(text(query))
            rows = result.fetchall()
        except Exception as e:
             logger.error(f"Error reading table {table_name}: {e}")
             return {"status": "error", "reason": str(e)}
        
        if not rows:
            return {"status": "skipped", "reason": "no_data"}
            
        columns = result.keys()
        df = pd.DataFrame(rows, columns=columns)
        
        # Calculate features
        df_calc = self.calculate_features(df.copy())
        
        # Check required features
        required_features = [
            "Energy_kWh", "Energy_per_kg", "Yield_loss_pct", 
            "RoomTemp_C", "CO2_per_kg", "Energy_x_Temp"
        ]
        
        # Validate features exist
        missing = [col for col in required_features if col not in df_calc.columns]
        if missing:
             # Check if we can proceed with partial features or just fail
             # For rigorous detection, we fail.
             logger.warning(f"Table {table_name} missing columns: {missing}. Skipping.")
             return {"status": "skipped", "reason": "missing_columns", "missing": missing}

        features = df_calc[required_features].values
        
        # Handle NaNs: skip rows with NaNs in required features
        valid_mask = ~np.isnan(features).any(axis=1)
        
        if not valid_mask.any():
              return {"status": "skipped", "reason": "no_valid_data_rows"}

        # Select valid data for prediction
        features_valid = features[valid_mask]
        
        # Scaling
        if self.scaler:
             features_scaled = self.scaler.transform(features_valid)
        else:
             features_scaled = features_valid
             
        # Predict
        predictions = self.model.predict(features_scaled)
        
        df_valid = df_calc[valid_mask].copy()
        df_valid["anomaly_flag"] = predictions
        
        # Calculate anomaly score (lower is more anomalous usually, but for visualization we might want absolute distance)
        try:
            # Decision function: negative for anomalies, positive for normal
            scores = self.model.decision_function(features_scaled)
            df_valid["anomaly_score"] = scores
        except:
             df_valid["anomaly_score"] = predictions # Fallback to binary
        
        # Determine severity
        df_valid["severity"] = df_valid.apply(self.determine_severity, axis=1)
        
        # Batch Update
        updates = {"RED": [], "AMBER": [], "GREEN": []}
        
        for _, row in df_valid.iterrows():
            record_id = row.get("id")
            severity = row.get("severity")
            if record_id and severity:
                updates[severity].append(str(record_id))
        
        try:
            for sev, ids in updates.items():
                if ids:
                    id_list = ", ".join(ids)
                    update_sql = f"UPDATE {table_name} SET anomaly_alert = '{sev}' WHERE id IN ({id_list})"
                    db.exec(text(update_sql))
            
            db.commit()
            logger.info(f"Updated anomaly_alert for {table_name}")
            
            # --- Persist to AnomalyDetection table ---
            try:
                # Filter for anomalies only (RED or AMBER)
                anomalies = df_valid[df_valid['severity'].isin(['RED', 'AMBER'])]
                
                for _, row in anomalies.iterrows():
                    ts = datetime.utcnow()
                    if 'upload_timestamp' in row and pd.notnull(row['upload_timestamp']):
                            ts = pd.to_datetime(row['upload_timestamp'])
                    elif 'date' in row and pd.notnull(row['date']):
                         try:
                             ts = pd.to_datetime(row['date'])
                         except:
                             pass
                    
                    if ts.tzinfo is not None:
                        ts = ts.tz_localize(None)

                    anomaly_entry = AnomalyDetection(
                        batch_id=str(row.get('batchid', 'unknown')),
                        timestamp=ts,
                        anomaly_score=float(row.get('anomaly_score', 0.0)),
                        is_anomaly=True,
                        severity=row.get('severity', 'AMBER'),
                        table_name=table_name,
                        energy_kwh=float(row.get('Energy_kWh', 0.0)) if pd.notnull(row.get('Energy_kWh')) else 0.0,
                        energy_per_kg=float(row.get('Energy_per_kg', 0.0)) if pd.notnull(row.get('Energy_per_kg')) else 0.0,
                        yield_loss_pct=float(row.get('Yield_loss_pct', 0.0)) if pd.notnull(row.get('Yield_loss_pct')) else 0.0,
                        co2_per_kg=float(row.get('CO2_per_kg', 0.0)) if pd.notnull(row.get('CO2_per_kg')) else 0.0,
                        room_temp_c=float(row.get('RoomTemp_C', 0.0)) if pd.notnull(row.get('RoomTemp_C')) else 0.0
                    )
                    db.add(anomaly_entry)
                
                db.commit()
                logger.info(f"Saved {len(anomalies)} anomalies to history.")
                
            except Exception as e:
                logger.error(f"Error saving anomaly history: {e}")
                db.rollback()
            # --------------------------------------
            

            
            return {
                "status": "success", 
                "anomalies": len(updates["RED"]) + len(updates["AMBER"]),
                "details": {k: len(v) for k, v in updates.items()}
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating anomaly alerts: {e}")
            return {"status": "error", "error": str(e)}

    # Preserving other methods like detect_anomalies if needed, but for now focusing on core flow

# Singleton instance
_anomaly_service = None

def get_anomaly_service() -> AnomalyDetectionService:
    """Get or create anomaly detection service instance."""
    global _anomaly_service
    if _anomaly_service is None:
        _anomaly_service = AnomalyDetectionService()
    return _anomaly_service
