import os
import psycopg2
import pandas as pd
import logging
from datetime import datetime
from jinja2 import Template
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from prometheus_client import Counter, Summary, start_http_server
import time

# Configuration for PostgreSQL database
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'security_systems'
DB_USER = 'your_user'
DB_PASSWORD = 'your_password'

# Email configuration for sending reports
SMTP_SERVER = 'smtp.example.com'
SMTP_PORT = 587
EMAIL_USER = 'your_email@example.com'
EMAIL_PASSWORD = 'your_password'
REPORT_RECIPIENT = 'recipient@example.com'

# Report storage directory
REPORT_DIR = './reports'
if not os.path.exists(REPORT_DIR):
    os.makedirs(REPORT_DIR)

# Prometheus metrics
REPORT_GENERATION_TIME = Summary('report_generation_time_seconds', 'Time spent generating reports')
REPORTS_SENT = Counter('reports_sent_total', 'Total number of reports sent')
EMAIL_ERRORS = Counter('email_errors_total', 'Total number of email errors')
REPORT_ERRORS = Counter('report_errors_total', 'Total number of report generation errors')

# Start Prometheus server for metric tracking
start_http_server(8001)

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("incident_report.log"), logging.StreamHandler()]
)

# Load data from PostgreSQL
def load_data_from_db():
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD
        )
        query = """
        SELECT * FROM prediction_logs
        WHERE timestamp >= NOW() - INTERVAL '1 day'
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        logging.info("Incident data loaded successfully.")
        return df
    except Exception as e:
        logging.error(f"Error loading data from database: {e}")
        REPORT_ERRORS.inc()
        return None

# Generate incident report using Jinja2 templates
@REPORT_GENERATION_TIME.time()  # Prometheus metric for tracking report generation time
def generate_incident_report(data, report_template, output_format='html'):
    try:
        with open(report_template) as file_:
            template = Template(file_.read())

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rendered_report = template.render(
            incidents=data.to_dict(orient='records'),
            timestamp=current_time
        )

        # Save report in desired format
        report_filename = f"incident_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{output_format}"
        report_filepath = os.path.join(REPORT_DIR, report_filename)

        if output_format == 'html':
            with open(report_filepath, 'w') as report_file:
                report_file.write(rendered_report)
        elif output_format == 'csv':
            data.to_csv(report_filepath, index=False)

        logging.info(f"Incident report generated: {report_filepath}")
        return report_filepath
    except Exception as e:
        logging.error(f"Error generating incident report: {e}")
        REPORT_ERRORS.inc()
        return None

# Send the incident report via email with retry and exponential backoff
def send_report_via_email(report_filepath, retry_count=3):
    attempt = 0
    while attempt < retry_count:
        try:
            # Prepare email content
            msg = MIMEMultipart()
            msg['Subject'] = 'Daily Security Incident Report'
            msg['From'] = EMAIL_USER
            msg['To'] = REPORT_RECIPIENT

            # Email body
            body = MIMEText("Please find the attached incident report for today's detected security issues.", 'plain')
            msg.attach(body)

            # Attach the report
            with open(report_filepath, 'rb') as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(report_filepath))
                part['Content-Disposition'] = f'attachment; filename="{}"'.format(os.path.basename(report_filepath))
                msg.attach(part)

            # Send the email
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASSWORD)
                server.sendmail(EMAIL_USER, REPORT_RECIPIENT, msg.as_string())

            logging.info(f"Incident report sent to {REPORT_RECIPIENT}.")
            REPORTS_SENT.inc()  # Increment reports sent counter
            break
        except Exception as e:
            EMAIL_ERRORS.inc()  # Increment email error counter
            logging.error(f"Error sending email report (Attempt {attempt + 1}): {e}")
            attempt += 1
            time.sleep(2 ** attempt)  # Exponential backoff
            if attempt == retry_count:
                logging.error("Failed to send email report after multiple attempts.")

# Main function for report generation and sending
def generate_and_send_incident_report():
    try:
        # Load data from the database
        incident_data = load_data_from_db()
        if incident_data is None or incident_data.empty:
            logging.info("No incidents detected in the past 24 hours.")
            return

        # Generate the incident report
        report_template = './templates/incident_report_template.html'  # Path to your HTML template
        report_filepath = generate_incident_report(incident_data, report_template, output_format='html')

        # Send the report via email
        if report_filepath:
            send_report_via_email(report_filepath)
    except Exception as e:
        logging.error(f"Error in generating or sending report: {e}")
        REPORT_ERRORS.inc()

if __name__ == "__main__":
    generate_and_send_incident_report()
