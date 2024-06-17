## Gemini Discord Bot Using Google VertexAI

## Introduction
Want to supercharge your Discord server with the mind-blowing power of Google's Gemini Pro? This bot is your portal to cutting-edge AI, right at your fingertips.  Imagine being able to:

* Generate awesome stories, poems, or even scripts for your next Discord roleplay.
* Analyze images shared in your server, instantly extracting text or getting cool image descriptions.
* Transcribe audio messages, so you can easily keep up with every conversation.
* Get AI insights and assistance on your code snippets, no matter how long they are!
   

## Features
- **Text generation using Gemini Pro:**  Unleash your creativity and write stories, poems, scripts, musical pieces, emails, letters, and anything else you can dream up!
- **Handles various input formats (using Gemini 1.5 Pro):** Let the bot analyze images, extract text from PDFs, transcribe audio, and more.
- **Accepts file input for processing text beyond Discord's character limit:** Have a super long code snippet you need help with?  No problem! This bot can handle it.
   

## Supported Input Formats
This bot welcomes a variety of formats, including:
- Text-based documents
- Data files
- Source code
- PDFs
- Images
- Audio files
- Video files

## Prerequisites
Before you start, you'll need:
- Python 3.8 or newer
- Discord Bot Token
- Google Cloud Platform account
- VertexAI enabled on your GCP project

## Setup Instructions
Ready to get started? It's easy!
1. Clone this repository to your local machine or server.
2. Install the required dependencies by running `pip install -r requirements.txt`.
3. Create a `.env` file in the root directory of the project and populate it with your environment variables as described below.

## Technical Details
This bot is built for flexibility! It uses the `gemini-1.5-pro-001` version of Google's Gemini Pro model by default, but you can easily switch to a different version (check out the `MODEL_ID` in `GeminiDiscordBot.py`). Oh, and by the way, this README.md?  Yeah, Gemini 1.5 Pro helped write this too! 

### Environment Variables
To get this bot up and running, you'll need to add these environment variables to your `.env` file:

- `GCP_REGION` - Your Google Cloud Platform region
- `GCP_PROJECT_ID` - Your Google Cloud Platform project ID
- `DISCORD_BOT_TOKEN` - Your Discord Bot Token

### Other Customization Options
Want to tweak things even further? Go for it!  You can customize the bot's behavior by exploring the source code. For example:

*  **Adjust the safety settings:** Control the level of content filtering applied to the bot's responses.
* **Modify the text generation parameters:** Play around with settings like `temperature` and `top_p` to change how creative and coherent the generated text is.
*  **Integrate additional commands:**  Add your own custom commands to make the bot even more powerful!

Go ahead, get creative, and make this bot your own!

## Running the Bot
Time to unleash the AI! To run the bot, just use this command:
```
python GeminiDiscordBot.py
```

Want to give the bot a fresh start?  Use this command to clear its memory of past conversations:
```
reset
```

## Contributions
Got some awesome ideas to make this bot even better? We'd love to hear them! Feel free to open an issue or submit a pull request.

## License
This project is licensed under the MIT License - see the LICENSE file for details.
