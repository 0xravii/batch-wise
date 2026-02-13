"""
Scheduler for Automated Model Monitoring Tasks

Provides scheduled execution of health checks and performance monitoring.
"""
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Optional

from app.ml.monitoring import daily_health_check_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelScheduler:
    """Scheduler for automated model monitoring tasks."""
    
    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = BackgroundScheduler()
        self.is_running = False
    
    def add_daily_health_check(self, hour: int = 6, minute: int = 0, table_name: str = None):
        """
        Add daily health check task.
        
        Args:
            hour: Hour to run (0-23), default 6 AM
            minute: Minute to run (0-59), default 0
            table_name: Optional table name for drift checks
        """
        trigger = CronTrigger(hour=hour, minute=minute)
        
        self.scheduler.add_job(
            func=daily_health_check_task,
            trigger=trigger,
            args=[table_name],
            id='daily_health_check',
            name='Daily Model Health Check',
            replace_existing=True
        )
        
        logger.info(f"Scheduled daily health check at {hour}:{minute:02d}")
    
    def add_weekly_report(self, day_of_week: str = 'mon', hour: int = 9):
        """
        Add weekly performance report task.
        
        Args:
            day_of_week: Day to run (mon, tue, wed, etc.)
            hour: Hour to run
        """
        trigger = CronTrigger(day_of_week=day_of_week, hour=hour)
        
        self.scheduler.add_job(
            func=self._weekly_report_task,
            trigger=trigger,
            id='weekly_report',
            name='Weekly Performance Report',
            replace_existing=True
        )
        
        logger.info(f"Scheduled weekly report on {day_of_week} at {hour}:00")
    
    def _weekly_report_task(self):
        """Generate and log weekly performance report."""
        logger.info("="*60)
        logger.info("WEEKLY PERFORMANCE REPORT")
        logger.info(f"Week ending: {datetime.now().strftime('%Y-%m-%d')}")
        logger.info("="*60)
        
        # Run health check
        checks = daily_health_check_task()
        
        # Additional weekly metrics could be calculated here
        # e.g., weekly anomaly trends, model drift analysis
        
        logger.info("Weekly report complete")
    
    def start(self):
        """Start the scheduler."""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Scheduler stopped")
    
    def list_jobs(self):
        """List all scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        logger.info(f"Scheduled jobs ({len(jobs)}):")
        for job in jobs:
            logger.info(f"  - {job.name} | Next run: {job.next_run_time}")
        return jobs


# Global scheduler instance
_scheduler = None

def get_scheduler() -> ModelScheduler:
    """Get or create scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = ModelScheduler()
    return _scheduler


def initialize_monitoring(
    enable_daily_check: bool = True,
    enable_weekly_report: bool = True,
    table_name: Optional[str] = None
):
    """
    Initialize and start monitoring schedule.
    
    Args:
        enable_daily_check: Enable daily health checks
        enable_weekly_report: Enable weekly reports
        table_name: Table name for drift monitoring
    """
    scheduler = get_scheduler()
    
    if enable_daily_check:
        scheduler.add_daily_health_check(hour=6, minute=0, table_name=table_name)
    
    if enable_weekly_report:
        scheduler.add_weekly_report(day_of_week='mon', hour=9)
    
    scheduler.start()
    
    logger.info("Monitoring initialized")
    return scheduler


if __name__ == "__main__":
    # Test scheduler
    scheduler = initialize_monitoring(
        enable_daily_check=True,
        enable_weekly_report=True
    )
    
    scheduler.list_jobs()
    
    print("\nScheduler running. Press Ctrl+C to stop...")
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()
        print("\nScheduler stopped")
