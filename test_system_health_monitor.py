import pytest
from system_health_monitor import check_system_health, generate_health_report

@pytest.fixture
def mock_health_data():
    return {
        'CCTV': {'online': 10, 'offline': 2},
        'AccessControl': {'online': 8, 'offline': 1}
    }

def test_check_system_health(mock_health_data, mocker):
    mocker.patch('system_health_monitor.fetch_system_data', return_value=mock_health_data)
    health_status = check_system_health()
    assert health_status['CCTV']['offline'] == 2

def test_generate_health_report(mock_health_data):
    report = generate_health_report(mock_health_data)
    assert "System Health Report" in report
