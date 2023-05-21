* * * 
* Create an HTML form that takes the necessary environment variables and performs validation. The form will be using in Discord by ADMIN who will be able to configure .env from Discord chat by submitting the HTMLform. 
* Here is an example of what your form could look like, with a Bootstrap CSS framework:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>.ENV File Form</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3" crossorigin="anonymous">
</head>
<body class="container mt-5">
    <form onsubmit="submitForm(event)">
        <!-- The form inputs go here, one for each environment variable. -->

        <div class="mb-3">
            <label for="flightsApiKey" class="form-label">FLIGHTS_API_KEY</label>
            <input type="text" class="form-control" id="flightsApiKey" required>
        </div>

        <!-- Repeat the above div block for each field in your .env file, replacing the "for" attribute in the label and the "id" attribute in the input with the correct environment variable name. -->
        
        <!-- ... -->

        <button type="submit" class="btn btn-primary">Submit</button>
    </form>
    <script>
        async function submitForm(ev) {
            ev.preventDefault();

            // Get the values from the form inputs.
            const flightsApiKey = document.getElementById('flightsApiKey').value;

            // Perform validation on the form inputs.
            // For example, check if the keys are in the right format.
            // This will depend on what you expect for each input.
            if (!flightsApiKey) {
                alert('The API key cannot be empty.');
                return;
            }

            // Prepare the data to be sent.
            const data = {
                FLIGHTS_API_KEY: flightsApiKey,
                // Add the other environment variables here.
            };

            // Send the data to your server.
            const response = await fetch('/save-env', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            // Check the response.
            if (response.ok) {
                alert('The .env file has been saved successfully!');
            } else {
                alert('There was an error. Please try again later.');
            }
        }
    </script>
</body>
</html>
```

You can add fields to the form for each environment variable in your `.env` file. Remember to replace `/save-env` in the `fetch` function with the actual URL of your server where you will be handling this request.
* * * 


################################################################################
### FLIGHTS_CHECKER_API .ENV
################################################################################

# The API key for accessing the flight data
FLIGHTS_API_KEY=
# Comma-separated list of airports to check flights for
AIRPORTS=MIA,LAX

# Comma-separated list of airlines to check flights for
AIRLINES=Vueling,BA

# Interval in minutes to check flight statuses
CHECK_INTERVAL=15

# Delay threshold in minutes after which a flight is considered delayed
DELAY_THRESHOLD=180

# Time to departure threshold in minutes
TIME_TO_DEPARTURE_THRESHOLD=180

# Start of the time window in minutes after delay print for acknowledging a cancelled flight
CANCELLED_FLIGHT_TIME_WINDOW_START=1

# End of the time window in minutes after delay print for acknowledging a cancelled flight
CANCELLED_FLIGHT_TIME_WINDOW_END=5

# Host for the flight data API
API_HOST=https://airlabs.co

# Endpoint for the flight schedules on the flight data API
API_ENDPOINT=schedules

# The API key for accessing the weather API
WEATHER_API_KEY=

# URL for the weather API
WEATHER_API_URL=http://api.weatherapi.com/v1/current.json

# Opening hours for the airports
MIA_OPENING_HOUR=8
MIA_CLOSING_HOUR=20
LAX_OPENING_HOUR=9
LAX_CLOSING_HOUR=18

# Non fault weather conditions
ENV_WEATHER=Lightening,Heavy_Snow 

# Zammad URL
ZAMMAD_URL=YOUR_ZAMMAD_URL

# Zammad token
ZAMMAD_TOKEN=YOUR_ZAMMAD_TOKEN

# List Monk URL
LIST_MONK_URL=YOUR_LIST_MONK_URL

# List Monk token
LIST_MONK_TOKEN=YOUR_LIST_MONK_TOKEN

# Discord bot token
DISCORD_BOT_TOKEN=YOUR_DISCORD_BOT_TOKEN

# Discord client ID
DISCORD_CLIENT_ID=x
* * * 




# For validating the data, you would have to add your validation conditions in the `submitForm` function. This could be in the form of regular expressions or checks for data type, length, format, etc. The exact implementation depends on each input.

To implement user authentication and access control (e.g., only admins can see the form), you might want to use something like a session-based authentication mechanism or a JWT (JSON Web Token) based authentication mechanism. The specifics would depend on your server setup and technology stack.

Example:



```javascript
const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');
const fs = require('fs');
const dotenv = require('dotenv');

const app = express();
app.use(bodyParser.json());

app.post('/save-env', (req, res) => {
    // Write the form data to the .env file.
    let content = '';
    for (let key in req.body) {
        content += `${key}=${req.body[key]}\n`;
    }
    fs.writeFileSync('.env', content);

    // Load the new environment variables.
    dotenv.config();

    // Send the updated .env file to the Airflow server.
    // Replace 'your-airflow-server-url' with your actual Airflow server URL.
    axios.post('your-airflow-server-url', {
        env: content
    })
    .then(response => {
        res.status(200).json({ message: 'The .env file has been saved successfully!' });
    })
    .catch(error => {
        console.error(error);
        res.status(500).json({ message: 'There was an error. Please try again later.' });
    });
});

app.listen(3000, () => {
    console.log('Server is listening on port 3000');
});
```

To set up this server, follow these steps:

1.  Install Node.js and npm, if you haven't already. You can download them from [here](https://nodejs.org/en/download/).
2.  Create a new directory for your project, then navigate to it in the command line.
3.  Initialize a new Node.js project with `npm init -y`.
4.  Install the necessary packages with `npm install express body-parser axios dotenv`.
5.  Create a new file in the project directory, then copy and paste the server code into the file.
6.  Replace `'your-airflow-server-url'` in the server code with your actual Airflow server URL.
7.  Start the server with `node your-filename.js`, replacing `'your-filename.js'` with the name of your file.

To use the HTML form, navigate to `localhost:3000` in your web browser, then fill out the form and click the "Submit" button. The form data will be sent to the server, which will update the .env file and send the updated file to the Airflow server.
