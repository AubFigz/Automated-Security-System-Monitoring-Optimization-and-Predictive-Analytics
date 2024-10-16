import pytest
import psycopg2
from data_collection import get_db_connection, create_database, fetch_cctv_data, batch_insert


@pytest.fixture
def db_connection():
    # Fixture to provide a database connection for tests
    conn = get_db_connection()
    yield conn
    conn.close()


def test_get_db_connection():
    # Test if the database connection is established
    conn = get_db_connection()
    assert conn is not None


def test_create_database(db_connection):
    # Test if tables are created successfully
    cursor = db_connection.cursor()
    create_database()
    cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'cctv_logs')")
    assert cursor.fetchone()[0] is True


def test_fetch_cctv_data(mocker):
    # Test API fetch function with mock data
    mock_response = {'status': 'online', 'motion_detected': 1}
    mocker.patch('data_collection.fetch_cctv_data', return_value=mock_response)
    response = fetch_cctv_data(None, 'CAM_001')
    assert response['status'] == 'online'
    assert response['motion_detected'] == 1


def test_batch_insert(db_connection):
    # Test data insertion
    cursor = db_connection.cursor()
    data = [{'timestamp': '2024-10-10 12:00:00', 'camera_id': 'CAM_001', 'status': 'online', 'motion_detected': 1}]
    batch_insert(cursor, 'cctv_logs', data)
    db_connection.commit()

    cursor.execute("SELECT COUNT(*) FROM cctv_logs")
    count = cursor.fetchone()[0]
    assert count > 0
