"""
Feature Engineering Module for Anomaly Detection

Extends the basic 6 features with advanced temporal, statistical, and equipment features.
Total features generated: 15
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Enhanced feature engineering for pharmaceutical batch anomaly detection."""
    
    def __init__(self):
        """Initialize feature engineer with configuration."""
        self.feature_config = {
            'temporal_features': True,
            'rolling_features': True,
            'equipment_features': True,
            'rolling_window': 10  # Last N batches for rolling stats
        }
    
    def calculate_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate basic KPI features (original 6 features).
        
        Features:
        1. Energy_kWh (direct)
        2. Energy_per_kg (efficiency)
        3. Yield_loss_pct (quality)
        4. RoomTemp_C (environmental)
        5. CO2_per_kg (sustainability)
        6. Energy_x_Temp (interaction)
        """
        # Column name standardization
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
        
        # 1. Energy per kg (efficiency)
        if "Energy_kWh" in df.columns and "OutputWeight_kg" in df.columns:
            df["Energy_per_kg"] = df["Energy_kWh"] / df["OutputWeight_kg"]
        
        # 2. Yield loss percentage (quality)
        if "InputWeight_kg" in df.columns and "OutputWeight_kg" in df.columns:
            df["Yield_loss_pct"] = (
                (df["InputWeight_kg"] - df["OutputWeight_kg"]) / df["InputWeight_kg"]
            ) * 100
        
        # 3. CO2 per kg (sustainability)
        if "Energy_kWh" in df.columns and "OutputWeight_kg" in df.columns:
            if "kg_co2_per_kwh" in df.columns:
                df["CO2_per_kg"] = (
                    df["Energy_kWh"] * df["kg_co2_per_kwh"]
                ) / df["OutputWeight_kg"]
            else:
                # Default CO2 factor if missing
                CO2_FACTOR = 0.5 
                df["CO2_per_kg"] = (df["Energy_kWh"] * CO2_FACTOR) / df["OutputWeight_kg"]
        
        # 4. Energy x Temperature interaction
        if "Energy_kWh" in df.columns and "RoomTemp_C" in df.columns:
            df["Energy_x_Temp"] = df["Energy_kWh"] * df["RoomTemp_C"]
        
        return df
    
    def calculate_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add temporal features for time-based pattern detection.
        
        New features:
        7. Batch_Hour (0-23)
        8. Batch_DayOfWeek (0-6, Monday=0)
        9. Time_Since_Last_Batch (minutes)
        """
        if not self.feature_config['temporal_features']:
            return df
        
        try:
            # Attempt to find timestamp column
            timestamp_col = None
            for col in ['upload_timestamp', 'timestamp', 'BatchDate', 'date', 'Date']:
                if col in df.columns:
                    timestamp_col = col
                    break
            
            if timestamp_col:
                # Convert to datetime
                df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors='coerce')
                
                # Extract hour of day
                df['Batch_Hour'] = df[timestamp_col].dt.hour
                
                # Extract day of week
                df['Batch_DayOfWeek'] = df[timestamp_col].dt.dayofweek
                
                # Time since last batch (in minutes)
                if len(df) > 1:
                    df = df.sort_values(timestamp_col)
                    time_diff = df[timestamp_col].diff()
                    df['Time_Since_Last_Batch'] = time_diff.dt.total_seconds() / 60
                    # Fill first row with median
                    df['Time_Since_Last_Batch'].fillna(
                        df['Time_Since_Last_Batch'].median(), 
                        inplace=True
                    )
                else:
                    df['Time_Since_Last_Batch'] = 0
                
                logger.info(f"Added temporal features using {timestamp_col}")
            else:
                logger.warning("No timestamp column found, skipping temporal features")
                # Add dummy features to maintain feature count consistency
                df['Batch_Hour'] = 12  # Default noon
                df['Batch_DayOfWeek'] = 2  # Default Wednesday
                df['Time_Since_Last_Batch'] = 60  # Default 1 hour
        
        except Exception as e:
            logger.error(f"Error calculating temporal features: {e}")
            # Fallback to defaults
            df['Batch_Hour'] = 12
            df['Batch_DayOfWeek'] = 2
            df['Time_Since_Last_Batch'] = 60
        
        return df
    
    def calculate_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add rolling statistics for trend detection.
        
        New features:
        10. Energy_kWh_Rolling_Mean (last 10 batches)
        11. Energy_kWh_Rolling_Std (variability)
        12. Yield_loss_pct_Rolling_Mean
        """
        if not self.feature_config['rolling_features']:
            return df
        
        window = self.feature_config['rolling_window']
        
        try:
            if 'Energy_kWh' in df.columns:
                df['Energy_kWh_Rolling_Mean'] = df['Energy_kWh'].rolling(
                    window=window, min_periods=1
                ).mean()
                df['Energy_kWh_Rolling_Std'] = df['Energy_kWh'].rolling(
                    window=window, min_periods=1
                ).std().fillna(0)
            
            if 'Yield_loss_pct' in df.columns:
                df['Yield_loss_pct_Rolling_Mean'] = df['Yield_loss_pct'].rolling(
                    window=window, min_periods=1
                ).mean()
            
            logger.info(f"Added rolling features with window={window}")
        
        except Exception as e:
            logger.error(f"Error calculating rolling features: {e}")
            # Fallback to current values
            if 'Energy_kWh' in df.columns:
                df['Energy_kWh_Rolling_Mean'] = df['Energy_kWh']
                df['Energy_kWh_Rolling_Std'] = 0
            if 'Yield_loss_pct' in df.columns:
                df['Yield_loss_pct_Rolling_Mean'] = df['Yield_loss_pct']
        
        return df
    
    def calculate_equipment_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add equipment and production stage features.
        
        New features:
        13. Machine_Batch_Count (cumulative batches per machine)
        14. ProductionStage_Encoded (one-hot encoding)
        15. Machine_Utilization (batches per day)
        """
        if not self.feature_config['equipment_features']:
            return df
        
        try:
            # Machine batch count
            if 'MachineName' in df.columns:
                df['Machine_Batch_Count'] = df.groupby('MachineName').cumcount() + 1
                logger.info("Added Machine_Batch_Count feature")
            else:
                df['Machine_Batch_Count'] = 1
            
            # Production stage encoding (simple label encoding)
            if 'ProductionStage' in df.columns:
                stage_mapping = {
                    'Mixing': 1,
                    'Granulation': 2,
                    'Drying': 3,
                    'Compression': 4,
                    'Coating': 5,
                    'Packaging': 6
                }
                df['ProductionStage_Encoded'] = df['ProductionStage'].map(stage_mapping).fillna(0)
                logger.info("Added ProductionStage_Encoded feature")
            else:
                df['ProductionStage_Encoded'] = 0
            
            # Machine utilization (batches per day)
            if 'MachineName' in df.columns and any(
                col in df.columns for col in ['upload_timestamp', 'timestamp', 'BatchDate']
            ):
                # Simplified: count batches per machine (full calculation needs time window)
                df['Machine_Utilization'] = df.groupby('MachineName')['Machine_Batch_Count'].transform('max')
            else:
                df['Machine_Utilization'] = 1
        
        except Exception as e:
            logger.error(f"Error calculating equipment features: {e}")
            df['Machine_Batch_Count'] = 1
            df['ProductionStage_Encoded'] = 0
            df['Machine_Utilization'] = 1
        
        return df
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Main method to engineer all features.
        
        Returns DataFrame with 15 features total.
        """
        logger.info(f"Starting feature engineering on {len(df)} rows")
        
        # Calculate features in order
        df = self.calculate_basic_features(df.copy())
        df = self.calculate_temporal_features(df)
        df = self.calculate_rolling_features(df)
        df = self.calculate_equipment_features(df)
        
        # Remove infinite and NaN values
        df = df.replace([np.inf, -np.inf], np.nan)
        
        logger.info(f"Feature engineering complete. Columns: {len(df.columns)}")
        
        return df
    
    def get_feature_names(self) -> List[str]:
        """Return list of all feature names in order."""
        features = [
            # Basic features (6)
            "Energy_kWh",
            "Energy_per_kg",
            "Yield_loss_pct",
            "RoomTemp_C",
            "CO2_per_kg",
            "Energy_x_Temp",
            # Temporal features (3)
            "Batch_Hour",
            "Batch_DayOfWeek",
            "Time_Since_Last_Batch",
            # Rolling features (3)
            "Energy_kWh_Rolling_Mean",
            "Energy_kWh_Rolling_Std",
            "Yield_loss_pct_Rolling_Mean",
            # Equipment features (3)
            "Machine_Batch_Count",
            "ProductionStage_Encoded",
            "Machine_Utilization"
        ]
        return features


# Singleton instance
_feature_engineer = None

def get_feature_engineer() -> FeatureEngineer:
    """Get or create feature engineer instance."""
    global _feature_engineer
    if _feature_engineer is None:
        _feature_engineer = FeatureEngineer()
    return _feature_engineer
