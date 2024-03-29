
# Gemini Discord Bot Using Google VertexAI

## Introduction
This project is a Discord Bot that utilizes Google VertexAI to call upon Gemini Pro for generating text based on user messages inluding images. It's designed to enhance Discord servers by providing AI-powered responses and content.

## Features
- Text generation using Gemini Pro
- Customizable through environment variables
- Easy to set up and deploy on any server

## Prerequisites
- Python 3.8 or newer
- Discord Bot Token
- Google Cloud Platform account
- VertexAI enabled on your GCP project

## Setup Instructions
1. Clone this repository to your local machine or server.
2. Install the required dependencies by running `pip install -r requirements.txt`.
3. Create a `.env` file in the root directory of the project and populate it with your environment variables as described below.

## Environment Variables
To run this project, you must add the following environment variables to your .env file:

- `GCP_REGION` - Your Google Cloud Platform region
- `GCP_PROJECT_ID` - Your Google Cloud Platform project ID
- `DISCORD_BOT_TOKEN` - Your Discord Bot Token
- `MAX_HISTORY` - The maximum number of messages to remember for generating context-aware responses

## Running the Bot
To run the bot, use the following command:
```
python GeminiDiscordBot.py
```

## Contributions
Contributions are welcome! Please open an issue or submit a pull request with your proposed changes or features.

## License
This project is licensed under the MIT License - see the LICENSE file for details.
