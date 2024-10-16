import pytest
import pandas as pd
from data_analysis_and_root_cause import analyze_cctv_motion_detection, analyze_cctv_failures

@pytest.fixture
def sample_cctv_data():
    # Sample data for CCTV logs
    data = {
        'timestamp': ['2024-10-10 12:00:00', '2024-10-10 12:05:00'],
        'camera_id': ['CAM_001', 'CAM_001'],
        'motion_detected': [1, 0],
        'status': ['online', 'offline']
    }
    return pd.DataFrame(data)

def test_analyze_cctv_motion_detection(sample_cctv_data):
    # Test motion detection analysis
    result = analyze_cctv_motion_detection(sample_cctv_data)
    assert result is not None  # Ensure analysis result is not None

def test_analyze_cctv_failures(sample_cctv_data):
    # Test anomaly detection (offline cameras)
    failures = analyze_cctv_failures(sample_cctv_data, threshold_minutes=1)
    assert len(failures) > 0  # Ensure failures are detected
