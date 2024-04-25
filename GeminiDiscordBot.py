# Gemini DiscordBot using vertexai
import os
import re
import aiohttp
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from PIL import Image
import io
import base64
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
image_generation_config = {
    "temperature": 0.4,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 2048,
}

safety_config = {
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_NONE,
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_NONE,
}

# Initialize Vertex AI
vertexai.init(project=GCP_PROJECT_ID, location=GCP_REGION)

# Load the model
MODEL_ID="gemini-1.5-pro-preview-0409"
image_model = generative_models.GenerativeModel(MODEL_ID)
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

async def process_attachments(message, cleaned_text):
    print(f"New Image Message FROM: {message.author.id}: {cleaned_text}")
    for attachment in message.attachments:
        file_extension = os.path.splitext(attachment.filename.lower())[1]
        ext_to_mime = {'.png': "image/png", '.jpg': "image/jpeg", '.jpeg': "image/jpeg", '.gif': "image/gif", '.webp': "image/webp"}
        if file_extension in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
            await message.add_reaction('🎨')
            mime_type = ext_to_mime[file_extension]
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as resp:
                    if resp.status != 200:
                        await message.channel.send('Unable to download the image.')
                        return
                    # Don't keep a record of image-based communication.
                    image_data = await resp.read()
                    resized_image_stream = resize_image_if_needed(image_data, file_extension)
                    resized_image_data = resized_image_stream.getvalue()
                    encoded_image_data = base64.b64encode(resized_image_data).decode("utf-8")
                    response_text = await generate_response_with_image_and_text(encoded_image_data, cleaned_text, mime_type)
                    await split_and_send_messages(message, response_text, MAX_DISCORD_LENGTH)
                    return
        else:
            supported_extensions = ', '.join(ext_to_mime.keys())
            await message.channel.send(f"🗑️ Unsupported file extension. Supported extensions are: {supported_extensions}")

async def async_send_message(chat_session, text):
    loop = asyncio.get_running_loop()

    try:
        # ThreadPoolExecutorを使用して、非同期で同期関数を実行
        response = await loop.run_in_executor(None, chat_session.send_message, text)
        return response
    except Exception as e:
        # エラーが発生した場合の処理
        print(f"Error sending message: {e}")
        # エラーに基づいた適切なレスポンスを返すか、Noneを返して呼び出し元で処理する
        return None
async def process_text_message(message, cleaned_text):
    """Processes a text message and generates a response using a chat model."""
    
    print(f"New Message FROM: {message.author.id}: {cleaned_text}")

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


async def generate_response_with_image_and_text(image_data, text, _mime_type):
    # Construct image and text parts with Part class
    image_part = Part.from_data(data=image_data, mime_type=_mime_type)
    text_part = Part.from_text(text=f"\n{text if text else 'What is this a picture of?'}")
    # Stored in list as prompt
    prompt_parts = [image_part, text_part]
    response = image_model.generate_content(prompt_parts,generation_config=image_generation_config,safety_settings=safety_config,)
    return response.text

def clean_discord_message(input_string):
    bracket_pattern = re.compile(r'<[^>]+>')
    return bracket_pattern.sub('', input_string)

def resize_image_if_needed(image_bytes, file_extension, max_size_mb=3, step=10):
    format_map = {'.png': 'PNG', '.jpg': 'JPEG', '.jpeg': 'JPEG', '.gif': 'GIF', '.webp': 'WEBP'}
    img_format = format_map.get(file_extension.lower(), 'JPEG')
    img_stream = io.BytesIO(image_bytes)
    img = Image.open(img_stream)
    while img_stream.getbuffer().nbytes > max_size_mb * 1024 * 1024:
        width, height = img.size
        img = img.resize((int(width * (100 - step) / 100), int(height * (100 - step) / 100)), Image.ANTIALIAS)
        img_stream = io.BytesIO()
        img.save(img_stream, format=img_format)
    return img_stream

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

