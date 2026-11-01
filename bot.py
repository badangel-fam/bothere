import os
import asyncio
import threading
from flask import Flask
import discord
from discord.ext import commands
from gtts import gTTS
import yt_dlp

# --- Flask Server สำหรับให้ UptimeRobot คอยยิงปลุก (กันบอทหลับ) ---
app = Flask('')

@app.route('/')
def home():
    return "I am alive and running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run_web)
    t.start()
# --------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

BOT_TOKEN = os.getenv("BOT_TOKEN")
raw_channel_id = os.getenv("VOICE_CHANNEL_ID")

try:
    TARGET_VOICE_CHANNEL_ID = int(raw_channel_id.strip()) if raw_channel_id else None
except Exception as e:
    print(f"Failed to parse channel ID: {e}")
    TARGET_VOICE_CHANNEL_ID = None

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:
        await bot.tree.sync()
        print("Slash commands synced successfully.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    bot.loop.create_task(connect_to_voice())

async def connect_to_voice():
    await bot.wait_until_ready()
    await asyncio.sleep(5)
    try:
        if not TARGET_VOICE_CHANNEL_ID:
            return
        channel = bot.get_channel(TARGET_VOICE_CHANNEL_ID)
        if channel and isinstance(channel, discord.VoiceChannel):
            if channel.guild.voice_client:
                await channel.guild.voice_client.disconnect(force=True)
            await channel.connect(self_deaf=True)
            print(f"Connected to voice channel: {channel.name}")
    except Exception as e:
        print(f"Voice connection error: {e}")

@bot.tree.command(name="say", description="พิมพ์ข้อความเพื่อให้บอทพูด")
async def say(interaction: discord.Interaction, text: str):
    voice_client = interaction.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        await interaction.response.send_message("บอทไม่ได้อยู่ในห้องเสียง!", ephemeral=True)
        return
    await interaction.response.send_message(f"พูดว่า: `{text}`", ephemeral=True)
    try:
        tts = gTTS(text=text, lang='th')
        path = "say.mp3"
        tts.save(path)
        while voice_client.is_playing():
            await asyncio.sleep(1)
        voice_client.play(discord.FFmpegPCMAudio(path))
    except Exception as e:
        print(f"TTS Error: {e}")

@bot.tree.command(name="play", description="เปิดเพลงจากลิงก์ YouTube")
async def play(interaction: discord.Interaction, url: str):
    voice_client = interaction.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        await interaction.response.send_message("บอทไม่ได้อยู่ในห้องเสียง!", ephemeral=True)
        return

    await interaction.response.send_message(f"กำลังโหลดเพลงจากลิงก์...", ephemeral=True)
    try:
        YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
            title = info.get('title', 'Unknown Title')

        while voice_client.is_playing():
            await asyncio.sleep(1)

        voice_client.play(discord.FFmpegPCMAudio(url2, options="-vn"))
        await interaction.followup.send(f"🎶 กำลังเล่นเพลง: **{title}**", ephemeral=True)
    except Exception as e:
        print(f"Play Error: {e}")
        await interaction.followup.send(f"เกิดข้อผิดพลาดในการเล่นเพลง: {e}", ephemeral=True)

@bot.tree.command(name="stop", description="หยุดเพลงและเคลียร์คิว")
async def stop(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await interaction.response.send_message("หยุดเพลงเรียบร้อย!", ephemeral=True)
    else:
        await interaction.response.send_message("ไม่มีเพลงกำลังเล่นอยู่", ephemeral=True)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if member.bot:
        return
    voice_client = member.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        return

    current_bot_channel = voice_client.channel
    msg = None
    if after.channel == current_bot_channel and before.channel != current_bot_channel:
        msg = f"อี {member.display_name} เสร่อเข้ามาแล้ว"
    elif before.channel == current_bot_channel and after.channel != current_bot_channel:
        msg = f"อี {member.display_name} อีช้างลากเย็ดไปไหนละอีควย"

    if msg:
        try:
            tts = gTTS(text=msg, lang='th')
            path = "notify.mp3"
            tts.save(path)
            while voice_client.is_playing():
                await asyncio.sleep(1)
            voice_client.play(discord.FFmpegPCMAudio(path))
        except Exception as e:
            print(f"Notify Error: {e}")

if __name__ == "__main__":
    keep_alive()
    if BOT_TOKEN:
        print("Waiting 15 seconds to avoid Discord Rate Limit...")
        import time
        time.sleep(15)
        bot.run(BOT_TOKEN)
    else:
        print("Error: BOT_TOKEN missing!")
