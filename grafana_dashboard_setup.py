import logging
import requests
import json
from grafana_api.grafana_face import GrafanaFace

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("grafana_dashboard_setup.log"), logging.StreamHandler()]
)

# Grafana connection details
GRAFANA_HOST = 'localhost'
GRAFANA_PORT = '3000'
GRAFANA_API_KEY = 'your_grafana_api_key'  # Replace with your Grafana API key
GRAFANA_URL = f"http://{GRAFANA_HOST}:{GRAFANA_PORT}/api"
GRAFANA_HEADERS = {"Authorization": f"Bearer {GRAFANA_API_KEY}", "Content-Type": "application/json"}

# Dashboard structure
DASHBOARD_TEMPLATE = {
    "dashboard": {
        "id": None,
        "title": "Security System Monitoring",
        "tags": ["security", "system", "monitoring"],
        "timezone": "browser",
        "panels": [],
        "schemaVersion": 26,
        "version": 0,
        "refresh": "5s"
    },
    "overwrite": True
}


# Panel template
def create_panel(title, datasource, metric, panel_id, x_pos, y_pos):
    panel = {
        "type": "graph",
        "title": title,
        "datasource": datasource,
        "id": panel_id,
        "gridPos": {"x": x_pos, "y": y_pos, "w": 12, "h": 8},
        "targets": [{
            "expr": metric,
            "legendFormat": "{{instance}}",
            "refId": "A"
        }],
        "lines": True,
        "fill": 1,
        "linewidth": 2,
        "points": False,
        "pointradius": 2,
        "stack": False,
        "aliasColors": {},
        "dashLength": 10,
        "dashes": False,
        "nullPointMode": "connected",
        "yaxes": [{"format": "short", "label": None, "logBase": 1, "min": 0}],
        "xaxis": {"show": True},
        "tooltip": {"shared": True, "sort": 0, "value_type": "individual"},
    }
    return panel


# Function to create a new Grafana dashboard
def create_dashboard():
    try:
        grafana_api = GrafanaFace(auth=GRAFANA_API_KEY, host=f"{GRAFANA_HOST}:{GRAFANA_PORT}")

        # Set up the base dashboard structure
        dashboard = DASHBOARD_TEMPLATE.copy()

        # Add panels to the dashboard
        datasource = "Prometheus"  # Assuming Prometheus as the datasource

        # Panel 1: CCTV System Uptime
        dashboard["dashboard"]["panels"].append(
            create_panel("CCTV System Uptime", datasource, "avg_over_time(cctv_uptime[5m])", panel_id=1, x_pos=0,
                         y_pos=0)
        )

        # Panel 2: Access Control Success Rate
        dashboard["dashboard"]["panels"].append(
            create_panel("Access Control Success Rate", datasource, "avg_over_time(access_control_success_rate[5m])",
                         panel_id=2, x_pos=12, y_pos=0)
        )

        # Panel 3: Intercom System Active/Inactive
        dashboard["dashboard"]["panels"].append(
            create_panel("Intercom System Status", datasource, "avg_over_time(intercom_status[5m])", panel_id=3,
                         x_pos=0, y_pos=8)
        )

        # Panel 4: Predicted System Failures
        dashboard["dashboard"]["panels"].append(
            create_panel("Predicted System Failures", datasource, "sum_over_time(predicted_failures[5m])", panel_id=4,
                         x_pos=12, y_pos=8)
        )

        # Panel 5: Alerts Triggered
        dashboard["dashboard"]["panels"].append(
            create_panel("Alerts Triggered", datasource, "sum_over_time(alerts_sent_total[5m])", panel_id=5, x_pos=0,
                         y_pos=16)
        )

        # Send the request to create the dashboard
        response = grafana_api.dashboard.update_dashboard(dashboard)
        if response["status"] == "success":
            logging.info(f"Dashboard created successfully: {response['uid']}")
        else:
            logging.error(f"Error creating dashboard: {response}")

    except Exception as e:
        logging.error(f"Failed to create Grafana dashboard: {e}")


# Function to check if the dashboard already exists
def dashboard_exists():
    try:
        response = requests.get(f"{GRAFANA_URL}/search?query=Security System Monitoring", headers=GRAFANA_HEADERS)
        if response.status_code == 200 and response.json():
            logging.info("Dashboard already exists.")
            return True
        else:
            logging.info("No existing dashboard found.")
            return False
    except Exception as e:
        logging.error(f"Failed to check existing dashboards: {e}")
        return False


# Main execution function
if __name__ == "__main__":
    if not dashboard_exists():
        create_dashboard()
    else:
        logging.info("No need to create a new dashboard.")
