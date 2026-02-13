# BatchWise Studio Backend

Production-ready backend for BatchWise Studio anomaly detection system.

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables:**
    Create a `.env` file with your database credentials:
    ```env
    DATABASE_URL=postgresql+pg8000://postgres:1234@localhost:5432/batchwise
    ```

3.  **Run Application:**
    ```bash
    python main.py
    ```
    API will be available at `http://localhost:8000`.

## Scripts

Located in `scripts/`:
- `setup_grafana.py`: Automates Grafana datasource and dashboard setup.
- `list_dashboards.py`: Utility to list available Grafana dashboards.
- `backfill_anomalies.py`: Manually triggers anomaly detection on existing data.

## Architecture

- `app/api`: API Endpoints
- `app/services`: Business logic (Anomaly Detection, etc.)
- `app/models`: Database models
- `app/core`: Configuration & Database connection
