import psycopg2
import pandas as pd
import numpy as np
import concurrent.futures
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
import logging
import sys

# Set up logging configuration for monitoring
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("data_preparation.log"), logging.StreamHandler(sys.stdout)]
)

# PostgreSQL connection details
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'security_systems'
DB_USER = 'your_user'
DB_PASSWORD = 'your_password'


# Load data from PostgreSQL with parallel processing
def load_data(query):
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD
        )
        df = pd.read_sql_query(query, conn)
        conn.close()
        logging.info(f"Data successfully loaded from query: {query}")
        return df
    except psycopg2.DatabaseError as e:
        logging.error(f"Error loading data from PostgreSQL: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return None


# Load all datasets in parallel
def load_all_data_parallel():
    queries = [
        ("SELECT * FROM cctv_logs", "cctv"),
        ("SELECT * FROM access_control_logs", "access_control"),
        ("SELECT * FROM intercom_logs", "intercom")
    ]

    def fetch_data(query_tuple):
        query, name = query_tuple
        logging.info(f"Loading data for {name}")
        return (name, load_data(query))

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(fetch_data, queries)

    data_dict = {name: df for name, df in results if df is not None}

    if len(data_dict) != len(queries):
        raise ValueError("Failed to load one or more datasets.")

    logging.info("Successfully loaded all data in parallel")
    return data_dict['cctv'], data_dict['access_control'], data_dict['intercom']


# Memory-efficient data types
def optimize_dtypes(df):
    for col in df.select_dtypes(include=['int', 'float']).columns:
        df[col] = pd.to_numeric(df[col], downcast='unsigned')
    logging.info(f"Optimized dtypes for DataFrame with {df.shape[0]} rows and {df.shape[1]} columns")
    return df


# Data Validation: Checking for duplicates or anomalies
def validate_data(df, dataset_name):
    try:
        # Remove duplicates
        if df.duplicated().any():
            logging.warning(f"Duplicates found in {dataset_name}, dropping duplicates")
            df.drop_duplicates(inplace=True)

        logging.info(f"Validation passed for {dataset_name}. Shape: {df.shape}")
    except Exception as e:
        logging.error(f"Error during data validation for {dataset_name}: {e}")
        raise


# Preprocessing and Feature Engineering
def preprocess_data(cctv_data, access_data, intercom_data):
    try:
        logging.info("Starting data preprocessing and feature engineering")

        # Convert timestamps to datetime
        cctv_data['timestamp'] = pd.to_datetime(cctv_data['timestamp'], errors='coerce')
        access_data['timestamp'] = pd.to_datetime(access_data['timestamp'], errors='coerce')
        intercom_data['timestamp'] = pd.to_datetime(intercom_data['timestamp'], errors='coerce')

        # Handle missing values by forward filling and dropping irrelevant rows
        cctv_data.fillna(method='ffill', inplace=True)
        access_data.fillna(method='ffill', inplace=True)
        intercom_data.fillna(method='ffill', inplace=True)

        # Optimize data types for efficiency
        cctv_data = optimize_dtypes(cctv_data)
        access_data = optimize_dtypes(access_data)
        intercom_data = optimize_dtypes(intercom_data)

        # Label encoding for categorical variables (status columns)
        le = LabelEncoder()
        cctv_data['status_encoded'] = le.fit_transform(cctv_data['status'])
        intercom_data['status_encoded'] = le.fit_transform(intercom_data['status'])

        # Feature Engineering: Time-based features
        cctv_data['hour_of_day'] = cctv_data['timestamp'].dt.hour
        access_data['hour_of_day'] = access_data['timestamp'].dt.hour
        intercom_data['hour_of_day'] = intercom_data['timestamp'].dt.hour

        # Create labels for CCTV failure (e.g., predict offline events)
        cctv_data['label_failure'] = (cctv_data['status'] == 'offline').astype(int)

        # Validate data for each dataset
        validate_data(cctv_data, 'CCTV Data')
        validate_data(access_data, 'Access Control Data')
        validate_data(intercom_data, 'Intercom Data')

        logging.info("Successfully preprocessed data")
        return cctv_data, access_data, intercom_data

    except Exception as e:
        logging.error(f"Error in preprocess_data: {e}")
        raise


# Feature Scaling to improve model convergence
def scale_features(X):
    try:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        logging.info("Features successfully scaled using StandardScaler")
        return X_scaled
    except Exception as e:
        logging.error(f"Error in scale_features: {e}")
        raise


# Save processed data to disk
def save_processed_data(cctv_data, access_data, intercom_data):
    try:
        cctv_data.to_csv('processed_cctv_data.csv', index=False)
        access_data.to_csv('processed_access_data.csv', index=False)
        intercom_data.to_csv('processed_intercom_data.csv', index=False)
        logging.info("Processed data successfully saved to disk")
    except Exception as e:
        logging.error(f"Error saving processed data to disk: {e}")
        raise


# Main function to handle data preparation
def main():
    try:
        # Load the data in parallel
        cctv_data, access_data, intercom_data = load_all_data_parallel()

        # Preprocess the data
        cctv_data, access_data, intercom_data = preprocess_data(cctv_data, access_data, intercom_data)

        # Split CCTV data into features and labels for modeling
        X_cctv = cctv_data[['motion_detected', 'is_online', 'hour_of_day']]
        y_cctv = cctv_data['label_failure']

        # Scale features
        X_cctv_scaled = scale_features(X_cctv)

        # Split the data into training and testing sets
        X_train, X_test, y_train, y_test = train_test_split(X_cctv_scaled, y_cctv, test_size=0.2, random_state=42)
        logging.info(f"Data split into training and testing sets. Training set size: {X_train.shape}")

        # Save the processed data for model training
        save_processed_data(cctv_data, access_data, intercom_data)

        logging.info("Data preparation completed successfully")
    except Exception as e:
        logging.error(f"Error in main function: {e}")
        raise


if __name__ == "__main__":
    main()
