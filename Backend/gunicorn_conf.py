import multiprocessing
import os

# Gunicorn configuration file
bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Environment variables
raw_env = [
    "DATABASE_URL=" + os.getenv("DATABASE_URL", ""),
    "ALLOWED_ORIGINS=" + os.getenv("ALLOWED_ORIGINS", "")
]
