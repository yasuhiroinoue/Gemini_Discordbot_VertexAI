# Gemini DiscordBot using vertexai
import os
import re
import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv
from PIL import Image
import io
import base64
import vertexai
from vertexai import generative_models
from vertexai.generative_models import Part

message_history = {}

load_dotenv()
GCP_REGION = os.getenv("GCP_REGION")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MAX_HISTORY = int(os.getenv("MAX_HISTORY"))


#---------------------------------------------AI Configuration-------------------------------------------------

# Configure the generative AI model
text_generation_config = {
    "temperature": 0.9,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 8192,
}
image_generation_config = {
    "temperature": 0.4,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 2048,
}

safety_config = {
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

# Initialize Vertex AI
vertexai.init(project=GCP_PROJECT_ID, location=GCP_REGION)

# Load the model
text_model = generative_models.GenerativeModel("gemini-pro")
image_model = generative_models.GenerativeModel("gemini-1.0-pro-vision")


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
                    if MAX_HISTORY == 0:
                        image_data = await resp.read()
                        resized_image_stream = resize_image_if_needed(image_data, file_extension)
                        resized_image_data = resized_image_stream.getvalue()
                        encoded_image_data = base64.b64encode(resized_image_data).decode("utf-8")
                        response_text = await generate_response_with_image_and_text(encoded_image_data, cleaned_text, mime_type)
                        await split_and_send_messages(message, response_text, 1700)
                        return
                    update_message_history(message.author.id, cleaned_text, "user")
                    formatted_history = get_formatted_message_history(message.author.id)
                    image_data = await resp.read()
                    resized_image_stream = resize_image_if_needed(image_data, file_extension)
                    resized_image_data = resized_image_stream.getvalue()
                    encoded_image_data = base64.b64encode(resized_image_data).decode("utf-8")
                    response_text = await generate_response_with_image_and_text(encoded_image_data, formatted_history, mime_type)
                    update_message_history(message.author.id, response_text, "model")
                    await split_and_send_messages(message, response_text, 1700)
        else:
            supported_extensions = ', '.join(ext_to_mime.keys())
            await message.channel.send(f"🗑️ Unsupported file extension. Supported extensions are: {supported_extensions}")

async def process_text_message(message, cleaned_text):
    print(f"New Message FROM: {message.author.id}: {cleaned_text}")
    if "RESET" in cleaned_text.upper():
        message_history.pop(message.author.id, None)
        await message.channel.send(f"🧹 History Reset for user: {message.author.name}")
        return
    await message.add_reaction('💬')
    if MAX_HISTORY == 0:
        response_text = await generate_response_with_text(cleaned_text)
        await split_and_send_messages(message, response_text, 1700)
        return
    update_message_history(message.author.id, cleaned_text, "user")
    formatted_history = get_formatted_message_history(message.author.id)
    response_text = await generate_response_with_text(formatted_history)
    update_message_history(message.author.id, response_text, "model")
    await split_and_send_messages(message, response_text, 1700)

#---------------------------------------------AI Generation History-------------------------------------------------

async def generate_response_with_text(message_text):
    prompt_parts = [message_text]
    print("Got textPrompt: " + message_text)
    response = text_model.generate_content(prompt_parts,generation_config=text_generation_config,safety_settings=safety_config,)
    return response.text

async def generate_response_with_image_and_text(image_data, text, _mime_type):
    # Construct image and text parts with Part class
    image_part = Part.from_data(data=image_data, mime_type=_mime_type)
    text_part = Part.from_text(text=f"\n{text if text else 'What is this a picture of?'}")
    # Stored in list as prompt
    prompt_parts = [image_part, text_part]
    response = image_model.generate_content(prompt_parts,generation_config=image_generation_config,safety_settings=safety_config,)
    return response.text

#---------------------------------------------Message History-------------------------------------------------

def update_message_history(user_id, text, message_type):
    # prefixed_message = f"{message_type}: {text}"
    # Construct the new message as a dictionary
    new_message = {'role': message_type, 'parts': [text]}
    if user_id in message_history:
        message_history[user_id].append(new_message)
        if len(message_history[user_id]) > MAX_HISTORY:
            message_history[user_id].pop(0)
    else:
        message_history[user_id] = [new_message]

def get_formatted_message_history(user_id):
    # Check if the user has any messages
    if user_id not in message_history or not message_history[user_id]:
        return "No messages found for this user."
    
    # Format each message in the history
    formatted_messages = []
    for message in message_history[user_id]:
        role = message['role']
        text = " ".join(message['parts'])  # Assuming 'parts' is a list of strings
        formatted_message = f"{role}: {text}"
        formatted_messages.append(formatted_message)
    
    # Join the formatted messages with double newlines
    return '\n\n'.join(formatted_messages)

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
    for i in range(0, len(text), max_length):
        await message_system.channel.send(text[i:i+max_length])

# Run the bot
bot.run(DISCORD_BOT_TOKEN)

