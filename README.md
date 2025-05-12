# Discord Economy Bot

A powerful Discord bot with advanced economy and interaction capabilities, offering dynamic user engagement through comprehensive game-like mechanics.

## Features

- Global currency system across all servers
- Advanced economy commands (work, daily, steal, gambling)
- Fun interaction commands
- Bank system with 10,000 coin limit and upgradeable with banknotes
- Shop with rotating stock that refreshes every 3 hours
- Web dashboard with real-time statistics
- Dual command system (prefix commands and slash commands)
- MongoDB integration for persistent data

## Technologies Used

- Discord.py for bot infrastructure
- MongoDB for persistent data management
- Flask for web dashboard
- Bootstrap with dark mode for UI
- Modular command architecture

## Deployment

This project is designed to be deployed on Render.com with two services:

1. **Discord Bot** (Worker Service) - Runs the bot functionality
2. **Web Dashboard** (Web Service) - Provides the admin interface

### Environment Variables

Required environment variables (set these in your Render dashboard):

```
TOKEN=your_discord_bot_token
MONGO_URI=your_mongodb_connection_string
SESSION_SECRET=your_random_session_secret
ADMIN_USERNAME=desired_admin_username
ADMIN_PASSWORD=secure_admin_password
STATUS_WEBHOOK_URL=discord_webhook_for_status_updates (optional)
```

## Local Development

### Prerequisites

- Python 3.8 or higher
- MongoDB instance
- Discord Developer Application with Bot Token

### Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your credentials
4. Run the bot: `python main.py --all`

### Running Components Separately

- Bot only: `python main.py --bot`
- Dashboard only: `python main.py --dashboard`
- Both components: `python main.py --all`

## License

MIT License

## Author

Discord ID: 545609811354583040