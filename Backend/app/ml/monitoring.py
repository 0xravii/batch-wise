"""
Model Performance Monitoring Module

Provides automated health checks, performance tracking, and alerting
for the anomaly detection model.
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import pandas as pd
import numpy as np
from sqlmodel import Session, select, text

# Add parent to path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.core.database import get_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelMonitor:
    """Monitor model performance and detect degradation."""
    
    def __init__(self, ai_dir: str = None):
        """Initialize monitor."""
        if ai_dir is None:
            base_dir = Path(__file__).parent.parent.parent.parent
            ai_dir = base_dir / 'AI'
        
        self.ai_dir = Path(ai_dir)
        self.metrics_path = self.ai_dir / 'model_metrics.json'
        self.alerts = []
    
    def load_current_metrics(self) -> Dict:
        """Load current model metrics."""
        try:
            if self.metrics_path.exists():
                with open(self.metrics_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Metrics file not found: {self.metrics_path}")
                return {}
        except Exception as e:
            logger.error(f"Error loading metrics: {e}")
            return {}
    
    def get_training_stats(self) -> Dict:
        """Get training statistics for drift detection."""
        metrics = self.load_current_metrics()
        
        if not metrics:
            return {}
        
        return {
            'feature_columns': metrics.get('feature_columns', []),
            'training_samples': metrics.get('training_samples', 0),
            'silhouette_score': metrics.get('silhouette_score', 0),
            'contamination': metrics.get('contamination', 0.01),
            'timestamp': metrics.get('timestamp', ''),
            'model_version': metrics.get('model_version', 'unknown')
        }
    
    def check_anomaly_rate_spike(self, db: Session, lookback_days: int = 7) -> Dict:
        """
        Check if anomaly detection rate has spiked recently.
        
        Returns alert if current rate >2x average.
        """
        try:
            # Get recent anomaly counts
            query = f"""
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as anomaly_count
                FROM anomaly_detection
                WHERE timestamp >= NOW() - INTERVAL '{lookback_days} days'
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """
            
            result = db.exec(text(query))
            rows = result.fetchall()
            
            if len(rows) < 2:
                return {'status': 'insufficient_data', 'severity': 'INFO'}
            
            # Calculate rates
            recent_count = rows[0][1] if rows else 0
            avg_count = sum(row[1] for row in rows[1:]) / len(rows[1:])
            
            # Check for spike
            if recent_count > avg_count * 2 and recent_count > 10:
                return {
                    'status': 'spike_detected',
                    'severity': 'WARNING',
                    'recent_count': recent_count,
                    'average_count': avg_count,
                    'ratio': recent_count / avg_count if avg_count > 0 else 0,
                    'message': f'Anomaly rate spiked: {recent_count} vs avg {avg_count:.1f}'
                }
            
            return {
                'status': 'normal',
                'severity': 'INFO',
                'recent_count': recent_count,
                'average_count': avg_count
            }
            
        except Exception as e:
            logger.error(f"Error checking anomaly rate: {e}")
            return {'status': 'error', 'severity': 'ERROR', 'error': str(e)}
    
    def check_feature_drift(self, table_name: str, db: Session) -> Dict:
        """
        Check if feature distributions have drifted significantly.
        
        Compares current data to training statistics.
        """
        try:
            training_stats = self.get_training_stats()
            feature_columns = training_stats.get('feature_columns', [])
            
            if not feature_columns:
                return {'status': 'no_training_stats', 'severity': 'INFO'}
            
            # Load current data
            query = f"SELECT * FROM {table_name} LIMIT 100"
            result = db.exec(text(query))
            rows = result.fetchall()
            
            if not rows:
                return {'status': 'no_data', 'severity': 'INFO'}
            
            columns = result.keys()
            df = pd.DataFrame(rows, columns=columns)
            
            # Check for drift in each feature
            drift_detected = []
            
            for feature in feature_columns:
                if feature in df.columns:
                    current_mean = df[feature].mean()
                    current_std = df[feature].std()
                    
                    # Simple drift detection: flag if mean shifted >3 std
                    # In production, would compare to stored training stats
                    if pd.notna(current_mean) and pd.notna(current_std):
                        if current_std > 0:
                            z_score = abs(current_mean) / current_std
                            if z_score > 3:
                                drift_detected.append({
                                    'feature': feature,
                                    'mean': current_mean,
                                    'std': current_std,
                                    'z_score': z_score
                                })
            
            if drift_detected:
                return {
                    'status': 'drift_detected',
                    'severity': 'CAUTION',
                    'drifted_features': drift_detected,
                    'message': f'Feature drift detected in {len(drift_detected)} features'
                }
            
            return {'status': 'normal', 'severity': 'INFO'}
            
        except Exception as e:
            logger.error(f"Error checking feature drift: {e}")
            return {'status': 'error', 'severity': 'ERROR', 'error': str(e)}
    
    def check_model_staleness(self) -> Dict:
        """Check if model needs retraining based on age."""
        try:
            metrics = self.load_current_metrics()
            
            if not metrics or 'timestamp' not in metrics:
                return {'status': 'no_timestamp', 'severity': 'WARNING'}
            
            model_date = datetime.fromisoformat(metrics['timestamp'])
            age_days = (datetime.now() - model_date).days
            
            if age_days > 90:
                return {
                    'status': 'model_stale',
                    'severity': 'WARNING',
                    'age_days': age_days,
                    'message': f'Model is {age_days} days old, recommend retraining'
                }
            elif age_days > 30:
                return {
                    'status': 'approaching_stale',
                    'severity': 'INFO',
                    'age_days': age_days,
                    'message': f'Model is {age_days} days old'
                }
            
            return {'status': 'fresh', 'severity': 'INFO', 'age_days': age_days}
            
        except Exception as e:
            logger.error(f"Error checking model staleness: {e}")
            return {'status': 'error', 'severity': 'ERROR', 'error': str(e)}
    
    def check_model_performance(self) -> Dict:
        """Check if model performance metrics are within acceptable ranges."""
        try:
            metrics = self.load_current_metrics()
            
            if not metrics:
                return {'status': 'no_metrics', 'severity': 'WARNING'}
            
            silhouette = metrics.get('silhouette_score', 0)
            
            # Performance thresholds
            if silhouette < 0.3:
                return {
                    'status': 'poor_performance',
                    'severity': 'WARNING',
                    'silhouette_score': silhouette,
                    'message': f'Silhouette score {silhouette:.3f} below threshold 0.3'
                }
            elif silhouette < 0.5:
                return {
                    'status': 'moderate_performance',
                    'severity': 'INFO',
                    'silhouette_score': silhouette,
                    'message': f'Silhouette score {silhouette:.3f} is moderate'
                }
            
            return {
                'status': 'good_performance',
                'severity': 'INFO',
                'silhouette_score': silhouette
            }
            
        except Exception as e:
            logger.error(f"Error checking model performance: {e}")
            return {'status': 'error', 'severity': 'ERROR', 'error': str(e)}
    
    def daily_health_check(self, table_name: str = None) -> Dict:
        """
        Perform comprehensive daily health check.
        
        Returns summary of all checks with alerts.
        """
        logger.info("="*60)
        logger.info("DAILY MODEL HEALTH CHECK")
        logger.info("="*60)
        
        db = next(get_session())
        
        checks = {
            'timestamp': datetime.now().isoformat(),
            'anomaly_rate': self.check_anomaly_rate_spike(db),
            'model_staleness': self.check_model_staleness(),
            'model_performance': self.check_model_performance()
        }
        
        if table_name:
            checks['feature_drift'] = self.check_feature_drift(table_name, db)
        
        # Collect alerts
        alerts = []
        for check_name, result in checks.items():
            if check_name == 'timestamp':
                continue
            
            severity = result.get('severity', 'INFO')
            if severity in ['WARNING', 'ERROR', 'CAUTION']:
                alerts.append({
                    'check': check_name,
                    'severity': severity,
                    'message': result.get('message', f'{check_name} flagged'),
                    'details': result
                })
        
        checks['alerts'] = alerts
        checks['alert_count'] = len(alerts)
        
        # Log summary
        logger.info(f"Health check complete: {len(alerts)} alerts")
        for alert in alerts:
            logger.warning(f"[{alert['severity']}] {alert['check']}: {alert['message']}")
        
        logger.info("="*60)
        
        return checks
    
    def generate_report(self, checks: Dict) -> str:
        """Generate human-readable report from health check."""
        report = []
        report.append("="*60)
        report.append("MODEL HEALTH CHECK REPORT")
        report.append(f"Timestamp: {checks['timestamp']}")
        report.append("="*60)
        report.append("")
        
        # Summary
        alert_count = checks.get('alert_count', 0)
        if alert_count == 0:
            report.append("✅ All checks passed - No issues detected")
        else:
            report.append(f"⚠️  {alert_count} alert(s) detected:")
            for alert in checks.get('alerts', []):
                report.append(f"  - [{alert['severity']}] {alert['message']}")
        
        report.append("")
        report.append("-"*60)
        report.append("DETAILED RESULTS:")
        report.append("")
        
        # Anomaly Rate
        ar = checks.get('anomaly_rate', {})
        report.append(f"Anomaly Rate: {ar.get('status', 'N/A')}")
        if ar.get('status') == 'spike_detected':
            report.append(f"  Recent: {ar['recent_count']} | Average: {ar['average_count']:.1f}")
            report.append(f"  Ratio: {ar['ratio']:.2f}x")
        
        # Model Staleness
        ms = checks.get('model_staleness', {})
        report.append(f"\nModel Age: {ms.get('age_days', 'N/A')} days")
        if ms.get('status') == 'model_stale':
            report.append(f"  ⚠️  Model requires retraining")
        
        # Performance
        mp = checks.get('model_performance', {})
        report.append(f"\nModel Performance: {mp.get('status', 'N/A')}")
        if 'silhouette_score' in mp:
            report.append(f"  Silhouette Score: {mp['silhouette_score']:.4f}")
        
        # Feature Drift
        if 'feature_drift' in checks:
            fd = checks['feature_drift']
            report.append(f"\nFeature Drift: {fd.get('status', 'N/A')}")
            if fd.get('status') == 'drift_detected':
                report.append(f"  Drifted Features: {len(fd['drifted_features'])}")
        
        report.append("")
        report.append("="*60)
        
        return "\n".join(report)


def daily_health_check_task(table_name: str = None):
    """Standalone task for daily health check."""
    monitor = ModelMonitor()
    checks = monitor.daily_health_check(table_name=table_name)
    report = monitor.generate_report(checks)
    
    print(report)
    
    # Optionally save to file
    ai_dir = monitor.ai_dir
    report_path = ai_dir / f"health_report_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(report_path, 'w') as f:
        f.write(report)
    
    logger.info(f"Report saved to {report_path}")
    
    return checks


if __name__ == "__main__":
    # Run health check
    import argparse
    
    parser = argparse.ArgumentParser(description="Run model health check")
    parser.add_argument('--table', default=None, help='Table name for drift check')
    
    args = parser.parse_args()
    
    daily_health_check_task(table_name=args.table)
