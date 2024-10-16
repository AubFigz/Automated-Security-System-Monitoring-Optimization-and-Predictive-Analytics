# system_health_monitor.py

import psycopg2
import logging
import smtplib
import time
import os
from email.mime.text import MIMEText
from prometheus_client import start_http_server, Summary, Counter, Gauge
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from asyncio import run, sleep
from smtplib import SMTPException

# PostgreSQL connection details (can be set via environment variables for Docker)
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'security_systems')
DB_USER = os.getenv('DB_USER', 'your_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'your_password')

# Email configuration for alerts (can be set via environment variables for Docker)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.example.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
EMAIL_USER = os.getenv('EMAIL_USER', 'your_email@example.com')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'your_password')
ALERT_EMAIL_RECIPIENT = os.getenv('ALERT_EMAIL_RECIPIENT', 'recipient@example.com')

# Prometheus metrics
uptime_check_time = Summary('uptime_check_processing_seconds', 'Time spent checking system uptime')
alerts_sent = Counter('alerts_sent', 'Total number of alerts sent')
cctv_status_gauge = Gauge('cctv_status', 'Number of offline CCTV cameras')
access_control_failures_gauge = Gauge('access_control_failures', 'Number of access control failures')

# Retry Configuration
MAX_RETRIES = 3
RETRY_COOLDOWN = 60  # Seconds between retries

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("system_health_monitor.log"), logging.StreamHandler()]
)

# Start Prometheus metrics server
start_http_server(8001)

# Retry decorator for PostgreSQL connection
def retry_with_backoff(retries=MAX_RETRIES, cooldown=RETRY_COOLDOWN):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    logging.warning(f"Error in {func.__name__}: {e}, retrying in {cooldown} seconds (attempt {attempt}/{retries})...")
                    time.sleep(cooldown)
            logging.error(f"Max retries exceeded for {func.__name__}.")
            raise Exception(f"Failed after {retries} retries.")
        return wrapper
    return decorator

# Asynchronous email alert sender
async def send_alert_email_async(subject, message):
    try:
        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = ALERT_EMAIL_RECIPIENT

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, ALERT_EMAIL_RECIPIENT, msg.as_string())

        logging.info(f"Alert email sent: {subject}")
        alerts_sent.inc()
    except SMTPException as e:
        logging.error(f"Error sending email: {e}")

# PostgreSQL connection helper
@retry_with_backoff()
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD
    )
    return conn

# Query database for offline CCTV cameras
@uptime_check_time.time()
def check_cctv_uptime(conn):
    try:
        cursor = conn.cursor()
        query = """
        SELECT camera_id, timestamp 
        FROM cctv_logs 
        WHERE status = 'offline' 
        AND timestamp >= NOW() - INTERVAL '10 minutes'
        """
        cursor.execute(query)
        offline_cameras = cursor.fetchall()
        cursor.close()

        if offline_cameras:
            camera_ids = ", ".join([f"Camera {cam[0]}" for cam in offline_cameras])
            message = f"ALERT: The following cameras are offline:\n{camera_ids}"
            run(send_alert_email_async("CCTV Offline Alert", message))

        # Update Prometheus gauge
        cctv_status_gauge.set(len(offline_cameras))
        logging.info(f"CCTV uptime check completed. Offline cameras: {len(offline_cameras)}")

    except Exception as e:
        logging.error(f"Error during CCTV uptime check: {e}")

# Query database for access control failures
def check_access_control_failures(conn):
    try:
        cursor = conn.cursor()
        query = """
        SELECT door_id, timestamp 
        FROM access_control_logs 
        WHERE access_granted = 0 
        AND timestamp >= NOW() - INTERVAL '10 minutes'
        """
        cursor.execute(query)
        failed_access_logs = cursor.fetchall()
        cursor.close()

        if failed_access_logs:
            door_ids = ", ".join([f"Door {log[0]}" for log in failed_access_logs])
            message = f"ALERT: The following doors had access failures:\n{door_ids}"
            run(send_alert_email_async("Access Control Failure Alert", message))

        # Update Prometheus gauge
        access_control_failures_gauge.set(len(failed_access_logs))
        logging.info(f"Access control failure check completed. Failures: {len(failed_access_logs)}")

    except Exception as e:
        logging.error(f"Error during access control failure check: {e}")

# Monitor system health for CCTV and Access Control in parallel
def monitor_system_health():
    try:
        conn = get_db_connection()
        if conn:
            logging.info("Starting system health monitoring...")

            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(check_cctv_uptime, conn),
                    executor.submit(check_access_control_failures, conn)
                ]
                for future in as_completed(futures):
                    future.result()

            conn.close()
        else:
            logging.error("Failed to establish a database connection.")

    except Exception as e:
        logging.error(f"Error in system health monitoring: {e}")

if __name__ == "__main__":
    try:
        while True:
            monitor_system_health()
            time.sleep(600)  # Run health checks every 10 minutes
    except KeyboardInterrupt:
        logging.info("System health monitoring stopped by user.")
    except Exception as e:
        logging.error(f"Unexpected error in main loop: {e}")