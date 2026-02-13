"""
Data Processing Service
Handles CSV parsing, table creation, and unified view management.
"""
import re
import csv
import io
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple
from fastapi import UploadFile, HTTPException
from sqlmodel import Session, select, text

from app.models.domain import CSVFileMetadata

logger = logging.getLogger(__name__)


def sanitize_table_name(filename: str) -> str:
    """Convert filename to a valid SQL table name with timestamp for uniqueness."""
    name = filename.replace('.csv', '')
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    if name and name[0].isdigit():
        name = 'csv_' + name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
    return f"csv_{name}_{timestamp}".lower()


    return metadata, records_created


def infer_column_type(sample_values: List[str], col_name: str = "") -> str:
    """Infer the most appropriate SQL type for a column based on sample values and name."""
    # Prioritize specific column names for better type safety
    col_lower = col_name.lower()
    if 'date' in col_lower or 'time' in col_lower:
        return 'TIMESTAMP'
    
    if not sample_values:
        return 'TEXT'
    
    clean_values = [v.strip() for v in sample_values if v and v.strip() not in ['', 'NULL', 'null', 'None']]
    
    if not clean_values:
        return 'TEXT'

    # Check for Boolean
    bool_values = {'true', 'false', 'yes', 'no', '1', '0', 'y', 'n'}
    if all(v.lower() in bool_values for v in clean_values):
        return 'BOOLEAN'
    
    # Check for Integer
    try:
        if all(float(v).is_integer() for v in clean_values if v.replace('.', '', 1).isdigit()):
             # rigorous check for integer string format like "123" not "123.0" unless we want float
             # Let's keep it simple: if it parses as int, it's int. But "1.0" is float in Python?
             # Actually, let's treat likely numerics as FLOAT to be safe in data analysis unless strictly ID
             pass
    except:
        pass

    # Check for Float (NumPy/Pandas style: if it looks like a number, store as float/numeric)
    try:
        for v in clean_values:
             float(v)
        return 'FLOAT'
    except ValueError:
        pass
        
    # Check for Date/Timestamp explicitly if not caught by name
    from dateutil.parser import parse
    try:
        for v in clean_values[:5]: # Check first few non-empty
            parse(v)
        return 'TIMESTAMP'
    except:
        pass
    
    return 'TEXT'


def create_dynamic_table(table_name: str, columns: Dict[str, str], db: Session) -> bool:
    """Create a dynamic table for CSV data."""
    try:
        columns_sql = []
        columns_sql.append("id SERIAL PRIMARY KEY")
        columns_sql.append("upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        
        for col_name, col_type in columns.items():
            safe_col = re.sub(r'[^a-zA-Z0-9_]', '_', col_name).lower()
            if col_name.lower() in ['id', 'upload_timestamp']:
                safe_col = f'csv_{safe_col}'
            
            if col_type == "INTEGER":
                sql_type = "INTEGER"
            elif col_type == "FLOAT":
                sql_type = "DOUBLE PRECISION" # Postgres float
            elif col_type == "BOOLEAN":
                sql_type = "BOOLEAN"
            elif col_type == "TIMESTAMP":
                sql_type = "TIMESTAMP"
            elif col_type == "DATE":
                sql_type = "DATE"
            else:
                sql_type = "TEXT"
            
            columns_sql.append(f"{safe_col} {sql_type}")
        
        # Add anomaly_alert column
        columns_sql.append("anomaly_alert TEXT DEFAULT NULL")
        
        create_table_sql = f"""
        CREATE TABLE {table_name} (
            {', '.join(columns_sql)}
        )
        """
        
        db.exec(text(create_table_sql))
        db.commit()
        logger.info(f"Created dynamic table: {table_name}")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating table {table_name}: {str(e)}")
        return False


def create_unified_view(db: Session):
    """
    Create a unified view combining all CSV tables for Grafana dashboard.
    This view automatically includes all uploaded CSV data, handling varying schemas.
    """
    try:
        # Get all CSV table metadata
        metadata_list = db.exec(select(CSVFileMetadata)).all()
        
        if not metadata_list:
            logger.info("No CSV tables found, skipping unified view creation")
            return
        
        # 1. Collect all unique columns across all tables
        all_columns = set()
        table_columns = {} # Map table_name -> set of its columns
        
        for metadata in metadata_list:
            try:
                # columns_info is a JSON string of col_name -> type
                cols_info = json.loads(metadata.columns_info)
                
                # Sanitize column names to match what's in the DB
                safe_cols = []
                for col_name in cols_info.keys():
                    safe_col = re.sub(r'[^a-zA-Z0-9_]', '_', col_name).lower()
                    if col_name.lower() in ['id', 'upload_timestamp']:
                         safe_col = f'csv_{safe_col}'
                    safe_cols.append(safe_col)
                
                # Add implicit columns that are always present
                safe_cols.extend(['id', 'upload_timestamp', 'anomaly_alert']) 
                
                table_columns[metadata.table_name] = set(safe_cols)
                all_columns.update(safe_cols)
                
            except Exception as e:
                logger.error(f"Error parsing metadata for {metadata.table_name}: {e}")
                continue

        if not all_columns:
             logger.warning("No columns found across tables.")
             return

        sorted_columns = sorted(list(all_columns))
        
        # 2. Build UNION ALL query
        union_queries = []
        for metadata in metadata_list:
            if metadata.table_name not in table_columns:
                continue
                
            current_table_cols = table_columns[metadata.table_name]
            select_parts = []
            
            # Add metadata columns
            select_parts.append(f"'{metadata.filename}'::text as source_filename")
            select_parts.append(f"'{metadata.table_name}'::text as source_table")
            select_parts.append(f"'{metadata.upload_timestamp}'::text as source_upload_time")
            
            # Add data columns (or NULL if missing)
            for col in sorted_columns:
                if col in current_table_cols:
                    # Explicitly cast numeric columns to DOUBLE PRECISION for consistent Grafana handling
                    # This prevents unit auto-scaling issues (e.g., kWh -> MWh)
                    col_lower = col.lower()
                    
                    # List of patterns that indicate numeric columns that should be cast
                    numeric_patterns = [
                        'kwh', 'energy', 'weight', 'temp', 'temperature', 
                        'kg', 'per_kg', 'loss', 'pct', 'percent', 'co2',
                        'pressure', 'humidity', 'speed', 'rate', 'value',
                        'count', 'score', 'factor'
                    ]
                    
                    is_numeric_col = any(pattern in col_lower for pattern in numeric_patterns)
                    
                    if is_numeric_col:
                        # Cast to DOUBLE PRECISION to ensure numeric type consistency
                        select_parts.append(f'CAST("{col}" AS DOUBLE PRECISION) as "{col}"')
                    elif 'timestamp' in col_lower or 'date' in col_lower or 'time' in col_lower:
                        # Preserve timestamp columns for Grafana time series
                        select_parts.append(f'"{col}"')
                    else:
                        # Text/other columns - select as-is
                        select_parts.append(f'"{col}"')
                else:
                    select_parts.append(f"NULL as \"{col}\"")
            
            query = f"SELECT {', '.join(select_parts)} FROM {metadata.table_name}"
            union_queries.append(query)
        
        if not union_queries:
             return

        # 3. Create or replace the unified view
        # Dropping view first to handle schema changes cleanly
        db.exec(text("DROP VIEW IF EXISTS csv_data_unified_view"))
        
        # We need to ensure the columns in the first SELECT define the types.
        # This is tricky with dynamic schemas. For now, we will SKIP creating the view if it causes issues,
        # or we accept that it might fail if user uploads conflicting types for same column name.
        # A robust solution casts all custom columns to TEXT in the view.
        # But that breaks Grafana ease of use.
        # Let's stick to the previous logic but uncomment it to actually create the view!
        
        view_sql = f"""
        CREATE OR REPLACE VIEW csv_data_unified_view AS
        {' UNION ALL '.join(union_queries)}
        """
        
        db.exec(text(view_sql))
        db.commit()
        
        logger.info(f"Created unified view with {len(metadata_list)} tables and {len(sorted_columns)} columns")
        
    except Exception as e:
        logger.error(f"Error creating unified view: {str(e)}")
        db.rollback()


async def process_csv_upload(file: UploadFile, db: Session) -> Tuple[CSVFileMetadata, int]:
    """Process CSV upload: parse, create table, insert data."""
    contents = await file.read()
    csv_content = contents.decode('utf-8')
    
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    
    if not csv_reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file has no columns")
    
    rows = list(csv_reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV file has no data rows")
    
    # Analyze column types
    columns_info = {}
    for col_name in csv_reader.fieldnames:
        sample_values = [row.get(col_name, '') for row in rows[:20]] # Check more rows
        col_type = infer_column_type(sample_values, col_name)
        columns_info[col_name] = col_type
    
    # Create unique table name
    table_name = sanitize_table_name(file.filename)
    
    # Create dynamic table
    if not create_dynamic_table(table_name, columns_info, db):
        raise HTTPException(status_code=500, detail="Failed to create table for CSV data")
    
    # Insert data
    records_created = 0
    current_utc_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    from dateutil.parser import parse
    
    for row in rows:
        columns = ['upload_timestamp'] + list(csv_reader.fieldnames)
        values = [f"'{current_utc_str}'"]
        
        for col_name in csv_reader.fieldnames:
            value = row.get(col_name, '').strip()
            col_type = columns_info.get(col_name, 'TEXT')
            
            if value in ['', 'NULL', 'null', 'None']:
                values.append('NULL')
                continue

            escaped_value = value.replace("'", "''")
            
            if col_type == 'TIMESTAMP' or col_type == 'DATE':
                try:
                    # Try to parse date string to standard format
                    dt = parse(value)
                    formatted_date = dt.strftime('%Y-%m-%d %H:%M:%S')
                    values.append(f"'{formatted_date}'")
                except:
                    # Fallback to original string if parse fails (shouldn't happen if type inferred accurately)
                    values.append(f"'{escaped_value}'")
            elif col_type in ['INTEGER', 'FLOAT', 'DOUBLE PRECISION']:
                 values.append(f"{escaped_value}") # No quotes for numbers
            elif col_type == 'BOOLEAN':
                 values.append(f"{escaped_value}")
            else:
                 values.append(f"'{escaped_value}'")
        
        safe_columns = []
        for col in columns:
            if col in ['id', 'upload_timestamp']:
                safe_col = col
            else:
                safe_col = re.sub(r'[^a-zA-Z0-9_]', '_', col).lower()
                if col.lower() in ['id', 'upload_timestamp']:
                    safe_col = f'csv_{safe_col}'
            safe_columns.append(safe_col)
        
        insert_sql = f"""
        INSERT INTO {table_name} ({', '.join(safe_columns)})
        VALUES ({', '.join(values)})
        """
        
        db.exec(text(insert_sql))
        records_created += 1
    
    # Record metadata
    metadata = CSVFileMetadata(
        filename=file.filename,
        table_name=table_name,
        upload_timestamp=datetime.utcnow(),
        record_count=records_created,
        columns_info=json.dumps(columns_info)
    )
    db.add(metadata)
    db.commit()
    
    # Refresh unified view
    create_unified_view(db)
    
    return metadata, records_created
