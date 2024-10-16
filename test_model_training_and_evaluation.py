import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from model_training_and_evaluation import tune_random_forest, train_logistic_regression
import pandas as pd
from sklearn.model_selection import train_test_split

@pytest.fixture
def training_data():
    # Generate synthetic training data
    X = pd.DataFrame({
        'motion_detected': [0, 1, 0, 1],
        'is_online': [1, 1, 0, 0],
        'hour_of_day': [12, 14, 6, 22]
    })
    y = [0, 1, 0, 1]  # Labels
    return X, y

def test_tune_random_forest(training_data):
    X, y = training_data
    rf_model = tune_random_forest(X, y)
    assert isinstance(rf_model, RandomForestClassifier)

def test_train_logistic_regression(training_data):
    X, y = training_data
    lr_model = train_logistic_regression(X, y)
    assert isinstance(lr_model, LogisticRegression)
