import asyncio
from http.server import BaseHTTPRequestHandler
from telegram.ext import Application, CommandHandler
from telegram import Bot
import logging
import requests
from datetime import datetime
from collections import defaultdict
import os
import json

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
API_FOOTBALL_KEY = os.getenv('API_FOOTBALL_KEY')
API_FOOTBALL_URL = 'https://v3.football.api-sports.io/'

headers = {
    'x-apisports-host': API_FOOTBALL_URL,
    'x-apisports-key': API_FOOTBALL_KEY
}

def fetch_predictions(fixture_id):
    url = f"{API_FOOTBALL_URL}predictions"
    querystring = {"fixture": fixture_id}
    response = requests.get(url, headers=headers, params=querystring)
    
    if response.status_code == 200:
        predictions_data = response.json()
        advice = predictions_data['response'][0]['predictions']['advice']
        return advice
    else:
        print(f"Error fetching prediction for fixture {fixture_id}: {response.status_code}")
        return None

def fetch_fixtures():
    leagues = ["333", "71"]  # Replace with league IDs for the leagues you want to be displayed
    all_fixtures = []
    league_fixtures = defaultdict(list)

    for league_id in leagues:
        url = f"{API_FOOTBALL_URL}fixtures"
        querystring = {
            "date":   "2024-08-03", #datetime.today().strftime('%Y-%m-%d'),
            "league": league_id,
            "season": "2024"
        }
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code == 200:
            fixtures = response.json().get('response', [])
            for fixture in fixtures:
                status = fixture['fixture']['status']['long']
                if status == "Not Started":
                    home_team = fixture['teams']['home']['name']
                    away_team = fixture['teams']['away']['name']
                    match_time = fixture['fixture']['date']
                    fixture_id = fixture['fixture']['id']
                    league_name = fixture['league']['name']
                    country = fixture['league']['country']
                    
                    # Fetch prediction for this fixture
                    prediction = fetch_predictions(fixture_id)
                    
                    fixture_info = {
                        'league': league_id,
                        'league_name': league_name,
                        'country': country,
                        'fixture_id': fixture_id,
                        'home_team': home_team,
                        'away_team': away_team,
                        'match_time': match_time,
                        'prediction': prediction
                    }
                    
                    # Add to the overall list
                    all_fixtures.append(fixture_info)
                    
                    # Add to the league-specific list
                    league_fixtures[league_id].append(fixture_info)
            
        else:
            print(f"Error fetching league {league_id}: {response.status_code}")
            print(f"Response Text: {response.text}")

    # Print fixtures by league
    for league_id, fixtures in league_fixtures.items():
        if fixtures:
            print(f"{fixtures[0]['country']} - {fixtures[0]['league_name']} Fixtures")
            for i, fixture in enumerate(fixtures, 1):
                match_time = datetime.fromisoformat(fixture['match_time']).strftime('%H:%M')
                print(f"{i}. {fixture['home_team']} vs {fixture['away_team']} at {match_time}")
                print(f"   Prediction: {fixture['prediction']}")
            print()  # Empty line between leagues

    return league_fixtures


async def format_and_send_fixtures(bot):
    league_fixtures = fetch_fixtures()

    if not any(fixtures for fixtures in league_fixtures.values()):
        logger.info("No fixtures found. No message sent.")
        return
    
    # Start with the overall title
    message = "*⚽ Next 24 hours matches and predictions 🤑*\n\n"
    
    for league_id, fixtures in league_fixtures.items():
        if fixtures:
            # Add league title
            message += f"*⚽ {fixtures[0]['country']} - {fixtures[0]['league_name']} Fixtures*\n\n"
            
            for i, fixture in enumerate(fixtures, 1):
                #match_time = datetime.fromisoformat(fixture['match_time']).strftime('%H:%M')
                message += f"{i}. {fixture['home_team']} vs {fixture['away_team']}\n"
                message += f"   🏆 Prediction: {fixture['prediction']}\n\n"
            
            # Add a separator between leagues
            message += "\n\n"
    
    # Remove the last separator
    message = message.rstrip("\n-")

     # Add the promotional sentences
    message += "\n\n"  # Add some space before the promotional content
    message += "Get 200% bonus 💰 on Melbet, use Promo code: BNS 👉 melbet.com\n"
    message += "For daily odds boost 🚀 use Promo code BST on 1Xbet 👉 1xbet.com"
    
    # Send the combined message
    await send_message_to_channel(bot, message)

async def send_message_to_channel(bot, message):
    try:
        # Split message if it's too long
        max_length = 4096  # Telegram's max message length
        if len(message) <= max_length:
            await bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode='Markdown')
        else:
            parts = [message[i:i+max_length] for i in range(0, len(message), max_length)]
            for part in parts:
                await bot.send_message(chat_id=CHANNEL_ID, text=part, parse_mode='Markdown')
        logger.info("Message(s) sent successfully")
    except Exception as e:
        logger.error(f"Error sending message: {e}")

async def start(update, context):
    await update.message.reply_text("Bot is running!")

# Initialize the application
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))

# The handler class for serverless function
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # Process the update
        application.process_update(json.loads(post_data))
        
        # Send fixtures
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        asyncio.run(format_and_send_fixtures(bot))
        
        self.send_response(200)
        self.end_headers()