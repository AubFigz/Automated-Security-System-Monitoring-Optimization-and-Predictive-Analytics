import psycopg2
import pandas as pd
import numpy as np
import logging
import joblib
import time
from sklearn.preprocessing import StandardScaler
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from concurrent.futures import ThreadPoolExecutor, as_completed

# Prometheus and Grafana API imports
from prometheus_client import start_http_server, Summary, Counter
from grafana_api.grafana_face import GrafanaFace

# Plotly Dash imports for web app
import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("model_integration.log"), logging.StreamHandler()]
)

# Load pre-trained models
rf_model = joblib.load('best_random_forest_model.pkl')
lr_model = joblib.load('logistic_regression_model.pkl')

# PostgreSQL connection details
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'security_systems'
DB_USER = 'your_user'
DB_PASSWORD = 'your_password'

# Email configuration for real-time alerts
SMTP_SERVER = 'smtp.example.com'
SMTP_PORT = 587
EMAIL_USER = 'your_email@example.com'
EMAIL_PASSWORD = 'your_password'
ALERT_EMAIL_RECIPIENT = 'recipient@example.com'

# Prometheus metrics
prediction_time = Summary('prediction_processing_seconds', 'Time spent processing prediction')
processed_data_count = Counter('processed_data_count', 'Total number of data points processed')
alerts_sent = Counter('alerts_sent', 'Total number of alerts sent')

# Start Prometheus server to expose metrics
start_http_server(8000)

# Grafana API setup
grafana = GrafanaFace(auth='your_grafana_token', host='localhost:3000')

# Real-time data loading from PostgreSQL
def load_real_time_data():
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD
        )
        query = """
        SELECT timestamp, motion_detected, is_online, hour_of_day
        FROM cctv_logs
        WHERE timestamp >= NOW() - INTERVAL '1 minute'
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        logging.info("Real-time data loaded successfully.")
        return df
    except Exception as e:
        logging.error(f"Error loading real-time data: {e}")
        return None

# Function to send email alerts with retry logic
def send_alert_email(message, retry_count=3):
    attempt = 0
    while attempt < retry_count:
        try:
            msg = MIMEText(message)
            msg['Subject'] = 'Security System Failure Prediction Alert'
            msg['From'] = EMAIL_USER
            msg['To'] = ALERT_EMAIL_RECIPIENT

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASSWORD)
                server.sendmail(EMAIL_USER, ALERT_EMAIL_RECIPIENT, msg.as_string())
            logging.info("Alert email sent successfully.")
            alerts_sent.inc()  # Increment alert count
            break
        except Exception as e:
            logging.error(f"Error sending email alert (Attempt {attempt + 1}): {e}")
            attempt += 1
            if attempt == retry_count:
                logging.error("Failed to send email alert after multiple attempts.")

# Function to preprocess incoming data with real-time feature engineering
def preprocess_data(df):
    try:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df.dropna(subset=['timestamp'], inplace=True)

        df['motion_avg'] = df['motion_detected'].rolling(window=3, min_periods=1).mean()
        df['online_delta'] = df['is_online'].diff().fillna(0)

        scaler = StandardScaler()
        df[['motion_detected', 'motion_avg', 'online_delta', 'hour_of_day']] = scaler.fit_transform(
            df[['motion_detected', 'motion_avg', 'online_delta', 'hour_of_day']]
        )
        logging.info("Real-time data preprocessed successfully.")
        return df
    except Exception as e:
        logging.error(f"Error preprocessing data: {e}")
        return None

# Predict system failures using pre-trained models
@prediction_time.time()  # Measure prediction time for Prometheus
def predict_failures(df):
    try:
        features = df[['motion_detected', 'motion_avg', 'online_delta', 'hour_of_day']]
        rf_predictions = rf_model.predict(features)
        lr_predictions = lr_model.predict(features)

        if np.mean(rf_predictions) > np.mean(lr_predictions):
            logging.info("Random Forest selected for prediction.")
            df['predictions'] = rf_predictions
        else:
            logging.info("Logistic Regression selected for prediction.")
            df['predictions'] = lr_predictions

        processed_data_count.inc(len(df))  # Track data processing count
        logging.info("Predictions made successfully.")
        return df
    except Exception as e:
        logging.error(f"Error during prediction: {e}")
        return None

# Handle real-time alerts based on predictions
def handle_alerts(df, threshold=0.5):
    try:
        failure_cases = df[df['predictions'] == 1]
        alert_threshold = threshold

        if len(failure_cases) >= alert_threshold:
            message = f"ALERT: Potential system failures detected!\n\n{failure_cases.to_string()}"
            send_alert_email(message)
            logging.info("Alerts triggered for potential failures.")
        else:
            logging.info("No failures predicted in this batch.")
    except Exception as e:
        logging.error(f"Error handling alerts: {e}")

# Save predictions to PostgreSQL for Grafana visualization
def save_predictions_to_db(df):
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD
        )
        cursor = conn.cursor()

        for index, row in df.iterrows():
            cursor.execute(
                """
                INSERT INTO prediction_logs (timestamp, motion_detected, motion_avg, online_delta, hour_of_day, predictions)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (row['timestamp'], row['motion_detected'], row['motion_avg'], row['online_delta'], row['hour_of_day'],
                 row['predictions'])
            )

        conn.commit()
        cursor.close()
        conn.close()
        logging.info("Predictions saved to PostgreSQL for Grafana.")
    except Exception as e:
        logging.error(f"Error saving predictions to PostgreSQL: {e}")

# Concurrently handle real-time monitoring for different data sources (CCTV, Access, Intercom)
def real_time_monitoring():
    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(monitor_data_source, "CCTV"), executor.submit(monitor_data_source, "Access"),
                       executor.submit(monitor_data_source, "Intercom")]
            for future in as_completed(futures):
                future.result()
    except KeyboardInterrupt:
        logging.info("Real-time monitoring stopped by user.")
    except Exception as e:
        logging.error(f"Error in real-time monitoring: {e}")
        raise

# Monitor data source (CCTV, Access, Intercom)
def monitor_data_source(source_type):
    while True:
        try:
            real_time_data = load_real_time_data()
            if real_time_data is None or real_time_data.empty:
                logging.info(f"No new data for {source_type}.")
                time.sleep(60)
                continue

            processed_data = preprocess_data(real_time_data)
            if processed_data is None or processed_data.empty:
                time.sleep(60)
                continue

            predictions_df = predict_failures(processed_data)
            if predictions_df is None:
                time.sleep(60)
                continue

            handle_alerts(predictions_df)
            save_predictions_to_db(predictions_df)

            time.sleep(60)

        except Exception as e:
            logging.error(f"Error in {source_type} monitoring: {e}")
            raise

# Plotly Dash web app for real-time monitoring
def run_dashboard():
    app = dash.Dash(__name__)

    def generate_plot(df):
        fig = px.line(df, x='timestamp', y='predictions', title='Real-Time Prediction Monitoring')
        return fig

    app.layout = html.Div(children=[
        html.H1(children='Security System Prediction Dashboard'),
        dcc.Graph(id='prediction-graph', figure=generate_plot(pd.read_sql_query("SELECT * FROM prediction_logs", psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)))),
        dcc.Interval(
            id='interval-component',
            interval=60*1000,  # in milliseconds
            n_intervals=0
        )
    ])

    @app.callback(
        Output('prediction-graph', 'figure'),
        Input('interval-component', 'n_intervals')
    )
    def update_graph_live(n):
        df = pd.read_sql_query("SELECT * FROM prediction_logs", psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD))
        return generate_plot(df)

    app.run_server(debug=True)

if __name__ == "__main__":
    real_time_monitoring()
    run_dashboard()  # Launch the real-time dashboard
