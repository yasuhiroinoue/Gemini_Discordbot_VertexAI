# Gemini DiscordBot using vertexai
import os
import re
import aiohttp
import asyncio
import magic
import discord
from discord.ext import commands
from dotenv import load_dotenv
import vertexai
from vertexai import generative_models
from vertexai.generative_models import Part

chat = {}

load_dotenv()
GCP_REGION = os.getenv("GCP_REGION")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
# The history is counted by the number of pairs of exchanges between the user and the assistant.

# The maximum number of characters per Discord message
MAX_DISCORD_LENGTH = 2000
#---------------------------------------------AI Configuration-------------------------------------------------

# Configure the generative AI model
text_generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    # "top_k": 1,
    "max_output_tokens": 8192,
}

safety_config = {
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
}

# Initialize Vertex AI
MODEL_ID="gemini-1.5-pro-001"
# MODEL_ID="gemini-1.5-flash-001"

vertexai.init(project=GCP_PROJECT_ID, location=GCP_REGION)

# Load the model
chat_model =  generative_models.GenerativeModel(model_name=MODEL_ID, generation_config=text_generation_config,safety_settings=safety_config,)

#---------------------------------------------Discord Code-------------------------------------------------
# Initialize Discord bot
bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

@bot.event
async def on_ready():
    print("----------------------------------------")
    print(f'Gemini Bot Logged in as {bot.user}')
    print("----------------------------------------")

#On Message Function
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.mention_everyone:
        await message.channel.send(f'{bot.user}です')
        return

    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        cleaned_text = clean_discord_message(message.content)
        async with message.channel.typing():
            if message.attachments:
                await process_attachments(message, cleaned_text)
            else:
                await process_text_message(message, cleaned_text)


def get_mime_type_from_bytes(byte_data):
    mime = magic.Magic(mime=True)
    mime_type = mime.from_buffer(byte_data)
   
    return mime_type

async def process_attachments(message, cleaned_text):
    for attachment in message.attachments:
        await message.add_reaction('📄')
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as resp:
                    if resp.status != 200:
                        await message.channel.send('Unable to download the file.')
                        return
                    file_data = await resp.read()
                    
                    mime_type = get_mime_type_from_bytes(file_data)
                    # For debug
                    # print(mime_type)
                    response_text = await generate_response_with_file_and_text(message, file_data, cleaned_text, mime_type)
                    await split_and_send_messages(message, response_text, MAX_DISCORD_LENGTH)
                    return
        except aiohttp.ClientError as e:
            await message.channel.send(f'Failed to download the file: {e}')
        except Exception as e:
            await message.channel.send(f'An unexpected error occurred: {e}')


async def async_send_message(chat_session, prompt): 
    loop = asyncio.get_running_loop()

    try:
        # ThreadPoolExecutorを使用して、非同期で同期関数を実行
        response = await loop.run_in_executor(None, chat_session.send_message, prompt)
        return response
    except Exception as e:
        # エラーが発生した場合の処理
        print(f"Error sending message: {e}")
        # エラーに基づいた適切なレスポンスを返すか、Noneを返して呼び出し元で処理する
        return None
    
async def process_text_message(message, cleaned_text):
    """Processes a text message and generates a response using a chat model."""
    
    # For debug
    # print(f"New Message FROM: {message.author.id}: {cleaned_text}")

    # Handle reset command
    if re.search(r'^RESET$', cleaned_text, re.IGNORECASE):
        chat.pop(message.author.id, None)
        await message.channel.send(f"🧹 History Reset for user: {message.author.name}")
        return

    await message.add_reaction('💬')

    # Send response, splitting if necessary
    response_text = await generate_response_with_text(message,cleaned_text)
    await split_and_send_messages(message, response_text, MAX_DISCORD_LENGTH)

async def generate_response_with_text(message, cleaned_text):
    global chat
    user_id = message.author.id

    # Get or create chat session
    chat_session = chat.get(user_id)
    if not chat_session:
        chat_session = chat_model.start_chat()
        chat[user_id] = chat_session
    
    try:
        # Generate response using the asynchronous send_message function
        answer = await async_send_message(chat_session, cleaned_text)
        if answer.candidates and answer.candidates[0].content.parts:
            return answer.candidates[0].content.parts[0].text
        else:
            return "No valid response received."
    except Exception as e:
        print(f"An error occurred: {e}")
        return "An error occurred while generating the response."

async def generate_response_with_file_and_text(message, file, text, _mime_type):
    # Construct image and text parts with Part class
    file_part = Part.from_data(data=file, mime_type=_mime_type)
    text_part = Part.from_text(text=f"\n{text if text else 'What is this?'}")
    # Stored in list as prompt
    prompt_parts = [file_part, text_part]

    global chat
    user_id = message.author.id

    # Get or create chat session
    chat_session = chat.get(user_id)
    if not chat_session:
        chat_session = chat_model.start_chat()
        chat[user_id] = chat_session
    
    try:
        # Generate response using the asynchronous send_message function
        answer = await async_send_message(chat_session, prompt_parts)
        if answer.candidates and answer.candidates[0].content.parts:
            return answer.candidates[0].content.parts[0].text
        else:
            return "No valid response received."
    except Exception as e:
        print(f"An error occurred: {e}")
        return "An error occurred while generating the response."

def clean_discord_message(input_string):
    bracket_pattern = re.compile(r'<[^>]+>')
    return bracket_pattern.sub('', input_string)

async def split_and_send_messages(message_system, text, max_length):
    """
    Splits the given text into chunks that respect word boundaries and sends them
    using the provided message system. Chunks are up to max_length characters long.

    :param message_system: An object representing the Discord messaging system,
                           assumed to have a `channel.send` method for sending messages.
    :param text: The text to be sent.
    :param max_length: The maximum length of each message chunk.
    """
    start = 0
    while start < len(text):
        # If remaining text is within the max_length, send it as one chunk.
        if len(text) - start <= max_length:
            await message_system.channel.send(text[start:])
            break

        # Find the last whitespace character before the max_length limit.
        end = start + max_length
        while end > start and text[end-1] not in ' \n\r\t':
            end -= 1

        # If no suitable whitespace is found, force break at max_length.
        if end == start:
            end = start + max_length

        # Send the text from start to end.
        await message_system.channel.send(text[start:end].strip())
        
        # Update start position for next iteration to continue after the last whitespace.
        start = end

# Run the bot
bot.run(DISCORD_BOT_TOKEN)

