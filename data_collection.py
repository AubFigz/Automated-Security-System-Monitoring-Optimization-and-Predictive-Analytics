import psycopg2
import asyncio
import aiohttp
import logging
from datetime import datetime
from aiohttp import ClientSession
import time

# PostgreSQL connection details
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'security_systems'
DB_USER = 'your_user'
DB_PASSWORD = 'your_password'

# Configuration for devices
CAMERA_COUNT = 200
DOOR_COUNT = 50
INTERCOM_COUNT = 20
BATCH_SIZE = 50
DATA_COLLECTION_INTERVAL = 60  # seconds between data collection cycles

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('SecuritySystemsLogger')

# PostgreSQL Database connection
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to PostgreSQL: {e}")
        raise e

# PostgreSQL table creation (if not exists)
def create_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS cctv_logs (
                        timestamp TIMESTAMP, 
                        camera_id TEXT, 
                        status TEXT, 
                        motion_detected INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS access_control_logs (
                        timestamp TIMESTAMP, 
                        door_id TEXT, 
                        access_granted INTEGER)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS intercom_logs (
                        timestamp TIMESTAMP, 
                        intercom_id TEXT, 
                        status TEXT)''')

    conn.commit()
    cursor.close()
    conn.close()

# Function to store data in PostgreSQL in batches
def batch_insert(cursor, table, data):
    if table == "cctv_logs":
        cursor.executemany('''INSERT INTO cctv_logs (timestamp, camera_id, status, motion_detected) 
                              VALUES (%s, %s, %s, %s)''',
                           [(d['timestamp'], d['camera_id'], d['status'], d['motion_detected']) for d in data])

    elif table == "access_control_logs":
        cursor.executemany('''INSERT INTO access_control_logs (timestamp, door_id, access_granted) 
                              VALUES (%s, %s, %s)''',
                           [(d['timestamp'], d['door_id'], d['access_granted']) for d in data])

    elif table == "intercom_logs":
        cursor.executemany('''INSERT INTO intercom_logs (timestamp, intercom_id, status) 
                              VALUES (%s, %s, %s)''',
                           [(d['timestamp'], d['intercom_id'], d['status']) for d in data])

# Asynchronous data fetchers for CCTV, Access Control, and Intercom
async def fetch_cctv_data(session, camera_id):
    url = f"http://api.example.com/cameras/{camera_id}/status"  # Replace with actual API endpoint
    async with session.get(url) as response:
        if response.status == 200:
            json_response = await response.json()
            return {
                "timestamp": datetime.now(),
                "camera_id": camera_id,
                "status": json_response.get("status", "offline"),
                "motion_detected": json_response.get("motion_detected", 0)
            }
        else:
            logger.error(f"Failed to fetch CCTV data for {camera_id}. Status code: {response.status}")
            return None

async def fetch_access_control_data(session, door_id):
    url = f"http://api.example.com/access-control/{door_id}/status"  # Replace with actual API endpoint
    async with session.get(url) as response:
        if response.status == 200:
            json_response = await response.json()
            return {
                "timestamp": datetime.now(),
                "door_id": door_id,
                "access_granted": json_response.get("access_granted", 0)
            }
        else:
            logger.error(f"Failed to fetch Access Control data for {door_id}. Status code: {response.status}")
            return None

async def fetch_intercom_data(session, intercom_id):
    url = f"http://api.example.com/intercoms/{intercom_id}/status"  # Replace with actual API endpoint
    async with session.get(url) as response:
        if response.status == 200:
            json_response = await response.json()
            return {
                "timestamp": datetime.now(),
                "intercom_id": intercom_id,
                "status": json_response.get("status", "inactive")
            }
        else:
            logger.error(f"Failed to fetch Intercom data for {intercom_id}. Status code: {response.status}")
            return None

# Gather data from all systems asynchronously
async def gather_data(fetch_func, entity_ids, session):
    tasks = []
    for entity_id in entity_ids:
        tasks.append(fetch_func(session, entity_id))
    results = await asyncio.gather(*tasks)
    return [result for result in results if result is not None]

# Main function to collect and store data
async def collect_and_store_data():
    create_database()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Lists of entity IDs
    camera_ids = [f"CAM_{i:03}" for i in range(1, CAMERA_COUNT + 1)]
    door_ids = [f"DOOR_{i:03}" for i in range(1, DOOR_COUNT + 1)]
    intercom_ids = [f"INT_{i:03}" for i in range(1, INTERCOM_COUNT + 1)]

    async with ClientSession() as session:
        while True:
            try:
                # Collect data from all systems asynchronously
                cctv_data = await gather_data(fetch_cctv_data, camera_ids, session)
                access_data = await gather_data(fetch_access_control_data, door_ids, session)
                intercom_data = await gather_data(fetch_intercom_data, intercom_ids, session)

                # Batch insert data into PostgreSQL
                for i in range(0, len(cctv_data), BATCH_SIZE):
                    batch_insert(cursor, "cctv_logs", cctv_data[i:i + BATCH_SIZE])

                for i in range(0, len(access_data), BATCH_SIZE):
                    batch_insert(cursor, "access_control_logs", access_data[i:i + BATCH_SIZE])

                for i in range(0, len(intercom_data), BATCH_SIZE):
                    batch_insert(cursor, "intercom_logs", intercom_data[i:i + BATCH_SIZE])

                conn.commit()
                logger.info("Data collected and stored successfully.")

            except Exception as e:
                logger.error(f"Error during data collection: {e}")

            # Wait before collecting the next set of data
            await asyncio.sleep(DATA_COLLECTION_INTERVAL)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    try:
        asyncio.run(collect_and_store_data())
    except KeyboardInterrupt:
        logger.info("Data collection stopped by user.")

