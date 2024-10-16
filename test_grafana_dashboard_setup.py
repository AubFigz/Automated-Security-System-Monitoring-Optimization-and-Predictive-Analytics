import pytest
from grafana_dashboard_setup import create_grafana_dashboard

def test_create_grafana_dashboard(mocker):
    # Mock Grafana API call
    mocker.patch('grafana_dashboard_setup.grafana_api', return_value={"status": "success"})
    result = create_grafana_dashboard()
    assert result['status'] == 'success'
