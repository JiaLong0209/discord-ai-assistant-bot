ps aux | grep bot.py

pkill -f "ENV_FILE=.env.shizuka python bot.py"
pkill -f "ENV_FILE=.env.takopi python bot.py"

