"""
Enhanced Model Training Script with Hyperparameter Optimization

Trains Isolation Forest with grid search over key hyperparameters,
implements time-series cross-validation, and generates comprehensive metrics.
"""
import os
import sys
import pandas as pd
import numpy as np
import joblib
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import ParameterGrid, TimeSeriesSplit
from sklearn.metrics import silhouette_score, davies_bouldin_score
from sqlmodel import Session, create_engine, select

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.ml.feature_engineering import get_feature_engineer
from app.core.database import get_session

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelTrainer:
    """Enhanced model trainer with hyperparameter optimization."""
    
    def __init__(self, output_dir: str = None):
        """Initialize trainer."""
        if output_dir is None:
            # Default to AI directory
            base_dir = Path(__file__).parent.parent.parent.parent
            output_dir = base_dir / 'AI'
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.feature_engineer = get_feature_engineer()
        self.best_model = None
        self.best_scaler = None
        self.best_params = None
        self.best_score = -np.inf
        self.training_history = []
    
    def load_training_data(self, table_name: str = None, csv_path: str = None) -> pd.DataFrame:
        """
        Load training data from database table or CSV file.
        
        Args:
            table_name: Name of database table to load
            csv_path: Path to CSV file
        
        Returns:
            DataFrame with raw data
        """
        if csv_path:
            logger.info(f"Loading data from CSV: {csv_path}")
            df = pd.read_csv(csv_path)
            return df
        
        elif table_name:
            logger.info(f"Loading data from database table: {table_name}")
            try:
                db = next(get_session())
                from sqlmodel import text
                query = f"SELECT * FROM {table_name}"
                result = db.exec(text(query))
                rows = result.fetchall()
                columns = result.keys()
                df = pd.DataFrame(rows, columns=columns)
                logger.info(f"Loaded {len(df)} rows from database")
                return df
            except Exception as e:
                logger.error(f"Error loading from database: {e}")
                raise
        
        else:
            raise ValueError("Must provide either table_name or csv_path")
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, List[str], pd.DataFrame]:
        """
        Prepare features for training.
        
        Returns:
            features: numpy array of feature values
            feature_names: list of feature column names
            df_processed: DataFrame with all calculated features
        """
        logger.info("Engineering features...")
        df_processed = self.feature_engineer.engineer_features(df.copy())
        
        feature_names = self.feature_engineer.get_feature_names()
        
        # Check which features are available
        available_features = [f for f in feature_names if f in df_processed.columns]
        missing_features = [f for f in feature_names if f not in df_processed.columns]
        
        if missing_features:
            logger.warning(f"Missing features: {missing_features}")
        
        if len(available_features) < 6:
            raise ValueError(f"Insufficient features. Found only: {available_features}")
        
        logger.info(f"Using {len(available_features)} features: {available_features}")
        
        # Extract feature matrix
        features = df_processed[available_features].values
        
        # Remove rows with NaN
        valid_mask = ~np.isnan(features).any(axis=1)
        features_clean = features[valid_mask]
        
        logger.info(f"Training samples after cleaning: {len(features_clean)} (removed {(~valid_mask).sum()} rows with NaN)")
        
        return features_clean, available_features, df_processed[valid_mask]
    
    def grid_search(
        self,
        X: np.ndarray,
        param_grid: Dict = None
    ) -> Tuple[IsolationForest, StandardScaler, Dict, float]:
        """
        Perform grid search over hyperparameters.
        
        Args:
            X: Feature matrix
            param_grid: Dictionary of parameters to search
        
        Returns:
            best_model, best_scaler, best_params, best_score
        """
        if param_grid is None:
            param_grid = {
                'n_estimators': [100, 200, 300],
                'contamination': [0.01, 0.02, 0.05],
                'max_features': [0.5, 0.75, 1.0],
                'max_samples': ['auto', 256]
            }
        
        logger.info(f"Starting grid search with {len(ParameterGrid(param_grid))} combinations")
        
        best_model = None
        best_scaler = None
        best_params = None
        best_score = -np.inf
        
        for params in ParameterGrid(param_grid):
            try:
                # Scale features
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)
                
                # Train model
                model = IsolationForest(
                    random_state=42,
                    **params
                )
                model.fit(X_scaled)
                
                # Predict and calculate silhouette score
                predictions = model.predict(X_scaled)
                
                # Only calculate silhouette if we have both classes
                if len(np.unique(predictions)) > 1:
                    score = silhouette_score(X_scaled, predictions)
                else:
                    # If only one class, use decision function variance
                    scores = model.decision_function(X_scaled)
                    score = -np.std(scores)  # Negative because lower std is worse
                
                logger.info(f"Params: {params} | Silhouette Score: {score:.4f}")
                
                # Track history
                self.training_history.append({
                    'params': params,
                    'silhouette_score': float(score),
                    'anomaly_rate': (predictions == -1).sum() / len(predictions)
                })
                
                if score > best_score:
                    best_score = score
                    best_model = model
                    best_scaler = scaler
                    best_params = params
            
            except Exception as e:
                logger.error(f"Error with params {params}: {e}")
                continue
        
        logger.info(f"Best silhouette score: {best_score:.4f}")
        logger.info(f"Best params: {best_params}")
        
        return best_model, best_scaler, best_params, best_score
    
    def cross_validate(
        self,
        X: np.ndarray,
        model: IsolationForest,
        scaler: StandardScaler,
        n_splits: int = 5
    ) -> Dict:
        """
        Perform time-series cross-validation.
        
        Args:
            X: Feature matrix
            model: Trained model
            scaler: Fitted scaler
            n_splits: Number of CV splits
        
        Returns:
            Dictionary of CV metrics
        """
        logger.info(f"Performing time-series cross-validation with {n_splits} splits")
        
        tscv = TimeSeriesSplit(n_splits=n_splits)
        cv_scores = []
        
        for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
            X_train, X_test = X[train_idx], X[test_idx]
            
            # Scale
            fold_scaler = StandardScaler()
            X_train_scaled = fold_scaler.fit_transform(X_train)
            X_test_scaled = fold_scaler.transform(X_test)
            
            # Train
            fold_model = IsolationForest(**model.get_params())
            fold_model.fit(X_train_scaled)
            
            # Evaluate on test set
            predictions = fold_model.predict(X_test_scaled)
            
            if len(np.unique(predictions)) > 1:
                score = silhouette_score(X_test_scaled, predictions)
            else:
                score = 0.0
            
            cv_scores.append(score)
            logger.info(f"Fold {fold+1}/{n_splits}: Silhouette={score:.4f}")
        
        cv_results = {
            'cv_scores': cv_scores,
            'mean_score': np.mean(cv_scores),
            'std_score': np.std(cv_scores),
            'min_score': np.min(cv_scores),
            'max_score': np.max(cv_scores)
        }
        
        logger.info(f"CV Mean Score: {cv_results['mean_score']:.4f} ± {cv_results['std_score']:.4f}")
        
        return cv_results
    
    def save_model(
        self,
        model: IsolationForest,
        scaler: StandardScaler,
        feature_names: List[str],
        metrics: Dict,
        version: str = None
    ) -> str:
        """
        Save model, scaler, and metrics.
        
        Returns:
            model_version string
        """
        if version is None:
            version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Save model
        model_path = self.output_dir / f"isolation_model_{version}.pkl"
        joblib.dump(model, model_path)
        logger.info(f"Saved model to {model_path}")
        
        # Also save as current model
        current_model_path = self.output_dir / "isolation_model.pkl"
        joblib.dump(model, current_model_path)
        logger.info(f"Saved current model to {current_model_path}")
        
        # Save scaler
        scaler_path = self.output_dir / f"feature_scaler_{version}.pkl"
        joblib.dump(scaler, scaler_path)
        
        current_scaler_path = self.output_dir / "feature_scaler.pkl"
        joblib.dump(scaler, current_scaler_path)
        logger.info(f"Saved scaler to {scaler_path}")
        
        # Save metrics
        metrics_data = {
            'model_version': version,
            'timestamp': datetime.now().isoformat(),
            'feature_columns': feature_names,
            **metrics
        }
        
        metrics_path = self.output_dir / f"model_metrics_{version}.json"
        with open(metrics_path, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        current_metrics_path = self.output_dir / "model_metrics.json"
        with open(current_metrics_path, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        logger.info(f"Saved metrics to {metrics_path}")
        
        # Save training history
        history_path = self.output_dir / f"training_history_{version}.json"
        with open(history_path, 'w') as f:
            json.dump(self.training_history, f, indent=2)
        
        return version
    
    def train(
        self,
        data_source: str,
        source_type: str = 'csv',
        param_grid: Dict = None,
        perform_cv: bool = True
    ) -> Dict:
        """
        Main training pipeline.
        
        Args:
            data_source: Table name or CSV path
            source_type: 'csv' or 'table'
            param_grid: Hyperparameter grid
            perform_cv: Whether to run cross-validation
        
        Returns:
            Dictionary with training results
        """
        logger.info("="*60)
        logger.info("ENHANCED ANOMALY DETECTION MODEL TRAINING")
        logger.info("="*60)
        
        # Load data
        if source_type == 'csv':
            df = self.load_training_data(csv_path=data_source)
        else:
            df = self.load_training_data(table_name=data_source)
        
        logger.info(f"Loaded {len(df)} rows")
        
        # Prepare features
        X, feature_names, df_processed = self.prepare_features(df)
        
        # Grid search
        model, scaler, params, score = self.grid_search(X, param_grid)
        
        if model is None:
            raise ValueError("Grid search failed to find any valid model")
        
        # Cross-validation
        cv_results = {}
        if perform_cv and len(X) >= 50:  # Need enough data for CV
            cv_results = self.cross_validate(X, model, scaler, n_splits=min(5, len(X)//10))
        else:
            logger.warning("Skipping CV: insufficient data")
        
        # Calculate final metrics
        X_scaled = scaler.transform(X)
        predictions = model.predict(X_scaled)
        decision_scores = model.decision_function(X_scaled)
        
        final_metrics = {
            'training_samples': int(len(X)),
            'n_features': len(feature_names),
            'silhouette_score': float(score),
            'anomalies_detected': int((predictions == -1).sum()),
            'anomaly_percentage': float((predictions == -1).sum() / len(predictions) * 100),
            **params,
            'cv_results': cv_results
        }
        
        # Try Davies-Bouldin score
        try:
            if len(np.unique(predictions)) > 1:
                db_score = davies_bouldin_score(X_scaled, predictions)
                final_metrics['davies_bouldin_score'] = float(db_score)
        except:
            pass
        
        # Save model
        version = self.save_model(model, scaler, feature_names, final_metrics)
        
        logger.info("="*60)
        logger.info("TRAINING COMPLETE")
        logger.info(f"Model Version: {version}")
        logger.info(f"Silhouette Score: {score:.4f}")
        logger.info(f"Anomaly Rate: {final_metrics['anomaly_percentage']:.2f}%")
        logger.info("="*60)
        
        return {
            'version': version,
            'metrics': final_metrics,
            'model': model,
            'scaler': scaler,
            'feature_names': feature_names
        }


def train_enhanced_model(
    data_source: str,
    source_type: str = 'csv',
    output_dir: str = None
) -> Dict:
    """
    Convenience function to train enhanced model.
    
    Args:
        data_source: Path to CSV or table name
        source_type: 'csv' or 'table'
        output_dir: Directory to save outputs
    
    Returns:
        Training results dictionary
    """
    trainer = ModelTrainer(output_dir=output_dir)
    results = trainer.train(data_source, source_type=source_type)
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train enhanced anomaly detection model")
    parser.add_argument('--data', required=True, help='CSV file path or table name')
    parser.add_argument('--type', default='csv', choices=['csv', 'table'], help='Data source type')
    parser.add_argument('--output', default=None, help='Output directory')
    
    args = parser.parse_args()
    
    results = train_enhanced_model(
        data_source=args.data,
        source_type=args.type,
        output_dir=args.output
    )
    
    print("\n" + "="*60)
    print("TRAINING RESULTS")
    print("="*60)
    print(f"Version: {results['version']}")
    print(f"Silhouette Score: {results['metrics']['silhouette_score']:.4f}")
    print(f"Features Used: {len(results['feature_names'])}")
    print(f"Training Samples: {results['metrics']['training_samples']}")
    print(f"Anomaly Rate: {results['metrics']['anomaly_percentage']:.2f}%")
    print("="*60)
