import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.models import XCom
import logging
import time

load_dotenv()

class FlightChecker:
    def __init__(self):
        try:
            # Load environment variables
            self.api_key = os.getenv("FLIGHTS_API_KEY")
            self.airports = os.getenv("AIRPORTS")
            self.airlines = os.getenv("AIRLINES")
            self.check_interval = int(os.getenv("CHECK_INTERVAL", "60")) * 60
            self.delay_threshold = int(os.getenv("DELAY_THRESHOLD", "0"))
            self.time_to_departure_threshold = int(os.getenv("TIME_TO_DEPARTURE_THRESHOLD", "0"))
            self.cancelled_flight_time_window_start = int(os.getenv("CANCELLED_FLIGHT_TIME_WINDOW_START", "0"))
            self.cancelled_flight_time_window_end = int(os.getenv("CANCELLED_FLIGHT_TIME_WINDOW_END", "0"))
            self.api_host = "https://airlabs.co/api/v9"
            self.api_endpoint = "schedules"
            self.airport_hours = self.parse_airport_hours(os.getenv("AIRPORT_HOURS", ""))
            self.last_delay_print_time = {}  # Stores the last delay print time for each airport

            self.validate_environment_variables()
        except Exception as e:
            logging.error(f"Error initializing FlightChecker: {str(e)}")
            raise

    def validate_environment_variables(self):
        """
        Validates the presence and validity of required environment variables.
        Raises a ValueError if any of the required variables are missing or empty.
        """
        required_variables = [
            "FLIGHTS_API_KEY", "AIRPORTS", "AIRLINES", "CHECK_INTERVAL", "DELAY_THRESHOLD",
            "TIME_TO_DEPARTURE_THRESHOLD", "CANCELLED_FLIGHT_TIME_WINDOW_START",
            "CANCELLED_FLIGHT_TIME_WINDOW_END", "AIRPORT_HOURS"
        ]
        for var in required_variables:
            if not os.getenv(var):
                raise ValueError(f"Environment variable {var} is missing or empty")

    def parse_airport_hours(self, env_str):
        """
        Parses the environment variable string for airport hours.
        The format is 'AIRPORT1:OPEN1-CLOSE1,AIRPORT2:OPEN2-CLOSE2,...'
        For example: 'BCN:6-23,AMS:3-23'
        Args:
            env_str (str): The environment variable string
        Returns:
            dict: A dictionary with airport codes as keys and tuples with open and close hours as values
        """
        airport_hours = {}
        pairs = env_str.split(',')
        for pair in pairs:
            if ':' not in pair:
                continue
            airport, hours = pair.split(':')
            open_hour, close_hour = map(int, hours.split('-'))
            airport_hours[airport] = (open_hour, close_hour)
        return airport_hours

    def load_flight_data(self, context):
        """
        Loads flight data from the API and stores it in XCom.
        Retries the API request with exponential backoff in case of failures.
        """
        try:
            url = f"{self.api_host}/{self.api_endpoint}?dep_iata={self.airports}&api_key={self.api_key}"
            retry_count = 0
            max_retries = 5
            while retry_count < max_retries:
                try:
                    response = requests.get(url)
                    response.raise_for_status()
                    flight_data = response.json()
                    # Store flight data in XCom
                    context['ti'].xcom_push(key='flight_data', value=flight_data)
                    break
                except requests.exceptions.RequestException as e:
                    logging.error(f"Failed to load flight data: {str(e)}")
                    logging.info(f"Retrying in {2 ** retry_count} seconds...")
                    time.sleep(2 ** retry_count)
                    retry_count += 1
            else:
                raise RuntimeError("Failed to load flight data after multiple retries")
        except Exception as e:
            logging.error(f"Error loading flight data: {str(e)}")
            raise

    def analyze_delays(self, context):
        """
        Analyzes flight delays for each airport and performs appropriate actions.
        """
        try:
            # Retrieve flight data from XCom
            flight_data = context['ti'].xcom_pull(key='flight_data')
            if flight_data is None:
                logging.warning("Flight data is not loaded")
                return

            for airport in self.airports.split(","):
                current_hour = datetime.now().hour
                opening_hour, closing_hour = self.airport_hours.get(airport, (0, 0))
                if opening_hour <= current_hour < closing_hour:
                    delayed_flights = []
                    for flight in flight_data:
                        if flight['dep_iata'] == airport and (
                                self.airlines == 'all' or flight['airline'] in self.airlines.split(",")):
                            dep_time = datetime.strptime(flight["dep_time"], "%Y-%m-%d %H:%M")
                            dep_delayed = int(flight["dep_delayed"])
                            status = flight["status"]
                            if dep_delayed > self.delay_threshold and dep_time > datetime.now() + timedelta(
                                    hours=self.time_to_departure_threshold):
                                delayed_flights.append(flight)

                    for flight_info in delayed_flights:
                        flight_iata = flight_info['flight_iata']
                        if airport in self.last_delay_print_time and flight_iata in self.last_delay_print_time[airport]:
                            continue  # Skip already processed delays

                        logging.info(f"Flight {flight_iata} is delayed for airport {airport}.")
                        context['ti'].xcom_push(key='flight_info', value=flight_info)
                        break  # Exit the loop after processing the first delayed flight

        except Exception as e:
            logging.error(f"Error analyzing delays: {str(e)}")
            raise

    def notify_plugin(self, context):
        flight_info = context['ti'].xcom_pull(key='flight_info')
        
        # Prepare the data for the API request
        data = {
            'flight_info': flight_info
        }

        try:
            # Make the API request to the AutoGPT app
            response = requests.post('http://autogpt-app/api/analyze-flight', json=data)
            response.raise_for_status()

            # Process the analysis result
            analysis_result = response.json()
            if analysis_result == 'Yes':
                # Perform additional actions for a positive analysis result
                logging.info("AutoGPT analysis result: Yes")
            elif analysis_result == 'No':
                # Perform additional actions for a negative analysis result
                logging.info("AutoGPT analysis result: No")
            else:
                # Handle unrecognized analysis result
                logging.warning("Unrecognized AutoGPT analysis result")
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to communicate with the AutoGPT app: {str(e)}")
            raise

default_args = {
    'start_date': datetime(2023, 5, 21),
    'retries': 1,
    'retry_delay': timedelta(minutes=1)
}

with DAG(
        'flight_checker',
        default_args=default_args,
        description='Flight Checker DAG',
        schedule_interval=timedelta(minutes=1),
        catchup=False
) as dag:
    flight_checker = FlightChecker()

    load_flight_data_task = PythonOperator(
        task_id='load_flight_data_task',
        python_callable=flight_checker.load_flight_data,
        provide_context=True,
        dag=dag,
    )

    analyze_delays_task = PythonOperator(
        task_id='analyze_delays_task',
        python_callable=flight_checker.analyze_delays,
        provide_context=True,
        dag=dag,
    )

    notify_plugin_task = PythonOperator(
        task_id='notify_plugin_task',
        python_callable=flight_checker.notify_plugin,
        provide_context=True,
        dag=dag,
    )

    load_flight_data_task >> analyze_delays_task >> notify_plugin_task





