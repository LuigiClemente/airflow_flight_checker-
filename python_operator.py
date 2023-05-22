# Import required modules
import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from airflow import DAG
from airflow.operators.python_operator import PythonOperator

# Load environment variables from the .env file
load_dotenv()

class FlightChecker:
    def __init__(self):
        # Retrieve the necessary variables from the environment
        self.api_key = os.getenv("FLIGHTS_API_KEY")
        self.airports = os.getenv("AIRPORTS").split(",")
        self.airlines = os.getenv("AIRLINES")
        if self.airlines != "all":
            self.airlines = self.airlines.split(",")
        self.check_interval = int(os.getenv("CHECK_INTERVAL", "60")) * 60
        self.delay_threshold = int(os.getenv("DELAY_THRESHOLD", "0"))
        self.time_to_departure_threshold = int(os.getenv("TIME_TO_DEPARTURE_THRESHOLD", "0"))
        self.cancelled_flight_time_window_start = int(os.getenv("CANCELLED_FLIGHT_TIME_WINDOW_START", "0"))
        self.cancelled_flight_time_window_end = int(os.getenv("CANCELLED_FLIGHT_TIME_WINDOW_END", "0"))
        self.api_host = os.getenv("API_HOST")
        self.api_endpoint = os.getenv("API_ENDPOINT")
        self.env_weather = os.getenv("ENV_WEATHER").split(",")

        # Define opening and closing hours for each airport
        self.airport_hours = {
            "BCN": (6, 23),
            "AMS": (3, 23)
        }

        self.last_delay_print_time = {}  # Stores the last delay print time for each airport

    def get_flight_info(self, airport: str, airline: str = ""):
        # Construct the URL with query parameters
        url = f"{self.api_host}/api/v9/{self.api_endpoint}?dep_iata={airport}&api_key={self.api_key}"
        if airline:
            url += f"&airline={airline}"

        print(f"Final URL is -> {url}")

        #payload = {'dep_iata' : 'BCN', 'api_key' : '5ae65766-97cd-4c28-9c01-284f43966b10'}

        response = requests.get(url) #, headers = payload)

        print(f'Response in JSON -> {response.json()}')

        print(f"Status Code for response is -> {response.status_code}")

        if response.status_code != 200:
            raise Exception(f"Request failed with status {response.status_code}")

        try:
            return response.json()
        except json.decoder.JSONDecodeError:
            raise Exception("Invalid JSON response")

    def check_flights(self, airport: str):
        current_hour = datetime.now().hour
        opening_hour, closing_hour = self.airport_hours.get(airport, (0, 0))
        if opening_hour <= current_hour < closing_hour:
            if self.airlines == "all":
                flight_infos = self.get_flight_info(airport)
            else:
                flight_infos = [info for airline in self.airlines for info in self.get_flight_info(airport, airline)]
            for flight_info in flight_infos:
                print(type(flight_info))
                print(flight_info)
                if "dep_time" in flight_info and "dep_delayed" in flight_info and "status" in flight_info:
                    dep_time = datetime.strptime(flight_info["dep_time"], "%Y-%m-%d %H:%M")
                    dep_delayed = int(flight_info["dep_delayed"])
                    status = flight_info["status"]
                    if dep_delayed > self.delay_threshold and dep_time > datetime.now() + timedelta(hours=self.time_to_departure_threshold):
                        print(f"Flight {flight_info['flight_iata']} is delayed.")
                        self.last_delay_print_time[airport] = datetime.now()
                        self.notify_plugin("Delayed", flight_info)

                    # Only acknowledge a cancelled flight if a delay has been printed for the same airport
                    if airport in self.last_delay_print_time:
                        time_since_last_delay = (datetime.now() - self.last_delay_print_time[airport]).total_seconds() / 60
                        if status == "cancelled" and self.cancelled_flight_time_window_start < time_since_last_delay < self.cancelled_flight_time_window_end:
                            print(f"Flight {flight_info['flight_iata']} is cancelled.")
                            self.notify_plugin("Cancelled", flight_info)
                else:
                    print(f"Missing key(s) in flight info for flight {flight_info.get('flight_iata', 'unknown')}. Skipping...")

    def notify_plugin(self, status, flight_info):
        # Method to notify a plugin, its implementation depends on your specific needs.
        pass

# Initialize the FlightChecker
flight_checker = FlightChecker()

# Define the default arguments for the tasks in the DAG.
default_args = {
    'start_date': datetime(2023, 5, 21),
    'retries': 1,
    'retry_delay': timedelta(minutes=1)
}

# Initialize the DAG
dag = DAG(
    'flight_checker',
    default_args=default_args,
    description='Flight Checker DAG',
    schedule_interval=timedelta(minutes=1),
    catchup=False
)

def check_flights():
    for airport in flight_checker.airports:
        flight_checker.check_flights(airport)

# Task: Flight Checking
flight_checking_task = PythonOperator(
    task_id='flight_checking_task',
    python_callable=check_flights,
    dag=dag,
)

# Define the dependencies between the tasks in the DAG
flight_checking_task

