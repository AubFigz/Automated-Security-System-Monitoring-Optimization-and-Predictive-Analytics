import pytest
from incident_report import generate_incident_report
import pandas as pd

@pytest.fixture
def sample_incident_data():
    # Sample incident data for report generation
    data = {
        'timestamp': ['2024-10-10 12:00:00', '2024-10-10 12:05:00'],
        'camera_id': ['CAM_001', 'CAM_001'],
        'motion_detected': [1, 0],
        'status': ['offline', 'offline']
    }
    return pd.DataFrame(data)

def test_generate_incident_report(sample_incident_data):
    # Test the generation of incident report
    report = generate_incident_report(sample_incident_data)
    assert "Incident Report" in report
    assert "offline" in report
