import pytest
from model_integration import preprocess_data, predict_failures, handle_alerts
import pandas as pd

@pytest.fixture
def sample_real_time_data():
    # Sample real-time data for predictions
    data = {
        'timestamp': ['2024-10-10 12:00:00', '2024-10-10 12:05:00'],
        'motion_detected': [1, 0],
        'is_online': [1, 0],
        'hour_of_day': [12, 14]
    }
    return pd.DataFrame(data)

def test_preprocess_data(sample_real_time_data):
    # Test preprocessing of real-time data
    processed_data = preprocess_data(sample_real_time_data)
    assert 'motion_avg' in processed_data.columns
    assert 'online_delta' in processed_data.columns

def test_predict_failures(sample_real_time_data, mocker):
    # Mock model predictions
    mock_rf_model = mocker.patch('model_integration.rf_model.predict', return_value=[1, 0])
    predictions = predict_failures(sample_real_time_data)
    assert 'predictions' in predictions.columns

def test_handle_alerts(sample_real_time_data, mocker):
    # Test alert handling (trigger email alert)
    mocker.patch('model_integration.send_alert_email', return_value=None)
    handle_alerts(sample_real_time_data, threshold=0.5)
    assert True  # If no exception, test passes
