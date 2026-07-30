import os
import logging
import pandas as pd

logger = logging.getLogger("DataCache")

# Global cache variables
_telemetry_df = None
_trend_df = None

def load_data_caches():
    """
    Loads telemetry and health trend history CSV files into memory.
    Called on FastAPI startup.
    """
    global _telemetry_df, _trend_df
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Load telemetry history
    telemetry_path = os.path.join(base_dir, "data", "telemetry_history.csv")
    if os.path.exists(telemetry_path):
        try:
            _telemetry_df = pd.read_csv(telemetry_path)
            # Pre-parse timestamps to strings to speed up operations
            _telemetry_df['timestamp'] = _telemetry_df['timestamp'].astype(str)
            logger.info(f"Successfully cached telemetry history: {_telemetry_df.shape[0]} rows.")
        except Exception as e:
            logger.error(f"Failed to load telemetry history CSV cache: {e}")
    else:
        logger.warning(f"Telemetry history CSV file not found at: {telemetry_path}")
        
    # 2. Load health trend history
    trend_path = os.path.join(base_dir, "data", "health_trend_history.csv")
    if os.path.exists(trend_path):
        try:
            _trend_df = pd.read_csv(trend_path)
            _trend_df['timestamp'] = _trend_df['timestamp'].astype(str)
            logger.info(f"Successfully cached health trend history: {_trend_df.shape[0]} rows.")
        except Exception as e:
            logger.error(f"Failed to load health trend history CSV cache: {e}")
    else:
        logger.warning(f"Health trend history CSV file not found at: {trend_path}")

def get_telemetry_history(transformer_id: str) -> pd.DataFrame:
    """
    Returns the telemetry history DataFrame filtered by transformer_id.
    """
    global _telemetry_df
    if _telemetry_df is None or _telemetry_df.empty:
        return pd.DataFrame()
    return _telemetry_df[_telemetry_df['transformer_id'] == transformer_id]

def get_trend_history(transformer_id: str) -> pd.DataFrame:
    """
    Returns the health trend history DataFrame filtered by transformer_id.
    """
    global _trend_df
    if _trend_df is None or _trend_df.empty:
        return pd.DataFrame()
    return _trend_df[_trend_df['transformer_id'] == transformer_id]

def get_latest_telemetry(transformer_id: str) -> dict:
    """
    Returns the latest telemetry snapshot (dict) for a transformer.
    """
    history_df = get_telemetry_history(transformer_id)
    if history_df.empty:
        return {}
    # Get the last row (which represents the most recent reading)
    latest_row = history_df.iloc[-1]
    return latest_row.to_dict()
