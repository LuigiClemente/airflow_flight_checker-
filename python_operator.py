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

# FlightChecker class definition. It has methods to check flights, get weather data and assess fault condition.
class FlightChecker:
    def __init__(self):
        # Load environment variables from the .env file
        load_dotenv()

        # Retrieve the necessary variables from environment
        # These include the API key, airports, airlines, API host, etc.
        self.api_key = os.getenv("API_KEY")
        self.airports = os.getenv("AIRPORTS").split(",")
        self.airlines = os.getenv("AIRLINES").split(",")
        self.check_interval = int(os.getenv("CHECK_INTERVAL")) * 60
        self.delay_threshold = int(os.getenv("DELAY_THRESHOLD"))
        self.time_to_departure_threshold = int(os.getenv("TIME_TO_DEPARTURE_THRESHOLD"))
        self.cancelled_flight_time_window_start = int(os.getenv("CANCELLED_FLIGHT_TIME_WINDOW_START"))
        self.cancelled_flight_time_window_end = int(os.getenv("CANCELLED_FLIGHT_TIME_WINDOW_END"))
        self.api_host = os.getenv("API_HOST")
        self.api_endpoint = os.getenv("API_ENDPOINT")
        self.api_url = os.getenv("API_URL")
        self.env_weather = os.getenv("ENV_WEATHER")

        # Define opening and closing hours for each airport
        self.airport_hours = {
            "MIA": (int(os.getenv("MIA_OPENING_HOUR")), int(os.getenv("MIA_CLOSING_HOUR"))),
            "LAX": (int(os.getenv("LAX_OPENING_HOUR")), int(os.getenv("LAX_CLOSING_HOUR"))),
        }

        self.last_delay_print_time = {}  # Stores the last delay print time for each airport

    # Function to get flight info from API
    def get_flight_info(self, airport: str, airline: str):
        params = {
            "api_key": self.api_key,
            "dep_iata": airport,
            "airline_iata": airline,
            "_fields": "flight_iata,flight_number,dep_time,dep_estimated,dep_actual,dep_delayed,status"
        }
        response = requests.get(f"{self.api_host}/{self.api_endpoint}", params=params)
        return response.json()

    # Function to check flight statuses
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
                    if status == "cancelled" and self.cancelled_flight_time_window_start < time_since_last_delay <self.cancelled_flight_time_window_end:
                        print(f"Flight {flight_info['flight_iata']} is cancelled.")
                        self.notify_plugin("Cancelled", flight_info)
                        self.assess_fault_condition("Cancelled", flight_info)

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

# Define the initial task which listens to the admin and sets environment variables accordingly.
def initial_task_callable():
    # Code that listens to the admin and sets environment variables accordingly goes here...
    pass

# Define the initial_task operator in the DAG
initial_task = PythonOperator(
    task_id='initial_task',
    python_callable=initial_task_callable,
    dag=dag,
)

# Define the task to check flights and weather conditions.
def check_flights_and_weather_conditions_callable():
    # Loop through all airports and airlines to check flights and get weather data
    for airport in flight_checker.airports:
        for airline in flight_checker.airlines:
            flight_checker.check_flights(airport, airline)
            # weather_data = flight_checker.get_weather_data(airport) # Uncomment this line when get_weather_data is implemented

# Define the check_flights_and_weather_task operator in the DAG
check_flights_and_weather_task = PythonOperator(
    task_id='check_flights_and_weather_task',
    python_callable=check_flights_and_weather_conditions_callable,
    dag=dag,
)

# Define the task to assess fault condition.
def assess_fault_condition_callable():
    # Loop through all airports and airlines to check flights, get weather data, and assess fault condition
    for airport in flight_checker.airports:
        for airline in flight_checker.airlines:
            flight_checker.check_flights(airport, airline)
            # weather_data = flight_checker.get_weather_data(airport) # Uncomment this line when get_weather_data is implemented
            # flight_checker.assess_fault_condition(weather_data) # Uncomment this line when assess_fault_condition is implemented

# Define the assess_fault_condition_task operator in the DAG
assess_fault_condition_task = PythonOperator(
    task_id='assess_fault_condition_task',
    python_callable=assess_fault_condition_callable,
    dag=dag,
)

# Define the task to activate a campaign or create a ticket.
def activate_campaign_or_ticket_callable():
    # Original activate_campaign_or_ticket code goes here...
    pass

# Define the activate_campaign_or_ticket_task operator in the DAG
activate_campaign_or_ticket_task = PythonOperator(
    task_id='activate_campaign_or_ticket_task',
    python_callable=activate_campaign_or_ticket_callable,
    dag=dag,
)

# Define the Discord Notification Task. This task sends a message to the Discord channel when all tasks are completed.
discord_notification_task = DiscordWebhookOperator(
    task_id='discord_notification_task',
    http_conn_id='discord_webhook_default',
    webhook_endpoint=discord_webhook_url,
    message='All tasks completed successfully.',
    dag=dag
)

# Define the dependencies between the tasks in the DAG
initial_task >> check_flights_and_weather_task
check_flights_and_weather_task >> assess_fault_condition_task
assess_fault_condition_task >> activate_campaign_or_ticket_task
activate_campaign_or_ticket_task >> discord_notification_task
