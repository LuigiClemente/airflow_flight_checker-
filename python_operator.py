# Import required modules
import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.discord.operators.discord_webhook import DiscordWebhookOperator

# Load environment variables from the .env file
load_dotenv()

# Get discord webhook url from environment variable
discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

class FlightChecker:
    def __init__(self):
        # Load environment variables from the .env file
        load_dotenv()

        # Retrieve the necessary variables from environment
        # These include the API key, airports, airlines, API host, etc.
        self.api_key = os.getenv("FLIGHTS_API_KEY")
        self.airports = os.getenv("AIRPORTS").split(",")
        self.airlines = os.getenv("AIRLINES").split(",")
        self.check_interval = int(os.getenv("CHECK_INTERVAL")) * 60
        self.delay_threshold = int(os.getenv("DELAY_THRESHOLD"))
        self.time_to_departure_threshold = int(os.getenv("TIME_TO_DEPARTURE_THRESHOLD"))
        self.cancelled_flight_time_window_start = int(os.getenv("CANCELLED_FLIGHT_TIME_WINDOW_START"))
        self.cancelled_flight_time_window_end = int(os.getenv("CANCELLED_FLIGHT_TIME_WINDOW_END"))
        self.api_host = os.getenv("API_HOST")
        self.api_endpoint = os.getenv("API_ENDPOINT")
        self.env_weather = os.getenv("ENV_WEATHER").split(",")

        # Define opening and closing hours for each airport
        self.airport_hours = {
            "MIA": (int(os.getenv("MIA_OPENING_HOUR")), int(os.getenv("MIA_CLOSING_HOUR"))),
            "LAX": (int(os.getenv("LAX_OPENING_HOUR")), int(os.getenv("LAX_CLOSING_HOUR"))),
        }

        self.last_delay_print_time = {}  # Stores the last delay print time for each airport

    def get_flight_info(self, airport: str, airline: str):
        params = {
            "api_key": self.api_key,
            "dep_iata": airport,
            "airline_iata": airline,
            "_fields": "flight_iata,flight_number,dep_time,dep_estimated,dep_actual,dep_delayed,status"
        }
        response = requests.get(f"{self.api_host}/{self.api_endpoint}", params=params)
        return response.json()

    def check_flights(self, airport: str, airline: str):
        current_hour = datetime.now().hour
        opening_hour, closing_hour = self.airport_hours[airport]
        if opening_hour <= current_hour < closing_hour:
            flight_infos = self.get_flight_info(airport, airline)
            for flight_info in flight_infos:
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

    def notify_plugin(self, status, flight_info):
        # Method to notify a plugin, it's implementation depends on your specific needs.
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

# Task 1: Setting up the Job on Discord using the ENV File Form
discord_setup_task = PythonOperator(
    task_id='discord_setup_task',
    python_callable=lambda: print("Setting up the job on Discord..."),
    dag=dag,
)

# Task 2: Flight Checking
flight_checking_task = PythonOperator(
    task_id='flight_checking_task',
    python_callable=lambda: [flight_checker.check_flights(airport, airline) for airport in flight_checker.airports for airline in flight_checker.airlines],
    dag=dag,
)

# Task 3: Weather Fault Validation
# Here we need to replace this with actual implementation
weather_fault_validation_task = PythonOperator(
    task_id='weather_fault_validation_task',
    python_callable=lambda: print("Checking weather faults..."),
    dag=dag,
)

# Task 4: Ticketing or Campaign Activation
# Here we need to replace this with actual implementation
ticketing_or_campaign_activation_task = PythonOperator(
    task_id='ticketing_or_campaign_activation_task',
    python_callable=lambda: print("Activating campaign or ticketing..."),
    dag=dag,
)

# Define the dependencies between the tasks in the DAG
discord_setup_task >> flight_checking_task >> weather_fault_validation_task >> ticketing_or_campaign_activation_task

