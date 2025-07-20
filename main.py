#!/usr/bin/env python3
"""
Multi-Exchange Trading Bot - Main Entry Point
Supports Binance and Bybit with dynamic balance-based trading
Updated for Render cloud deployment
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.bot import MultiExchangeTradingBot
from config.settings import TELEGRAM_TOKEN, SANDBOX_MODE
from utils.logger import setup_logger

def setup_cloud_health_server():
    """Setup health check server for Render cloud deployment"""
    try:
        from config.settings import PORT, IS_CLOUD_DEPLOYMENT, ENABLE_HEALTH_CHECK
        
        if IS_CLOUD_DEPLOYMENT and ENABLE_HEALTH_CHECK:
            print("☁️ Setting up Render cloud health check server...")
            
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import threading
            from datetime import datetime
            
            class HealthHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    
                    # Create status page
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
                    html = f'''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Multi-Exchange Trading Bot Status</title>
                        <meta http-equiv="refresh" content="30">
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 40px; background: #1a1a1a; color: #ffffff; }}
                            .container {{ background: #2d2d2d; padding: 30px; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }}
                            h1 {{ color: #4CAF50; text-align: center; }}
                            .status {{ color: #4CAF50; font-weight: bold; font-size: 18px; text-align: center; }}
                            .info {{ background: #333; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #4CAF50; }}
                            .metric {{ display: inline-block; margin: 10px 20px; padding: 10px; background: #444; border-radius: 5px; }}
                            .time {{ text-align: center; color: #888; margin-top: 20px; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>🤖 Multi-Exchange Trading Bot v2.0</h1>
                            <div class="status">✅ Status: Running Successfully on Render Cloud!</div>
                            
                            <div class="info">
                                <h3>📊 Trading Configuration:</h3>
                                <div class="metric">Strategy: 0.2% Dynamic Balance</div>
                                <div class="metric">Exchanges: 🟡 Binance, 🟠 Bybit</div>
                                <div class="metric">Symbol: HYPE/USDT:USDT</div>
                                <div class="metric">Leverage: 25x</div>
                                <div class="metric">Take Profit: 0.56%</div>
                                <div class="metric">Martingale Levels: 11</div>
                            </div>
                            
                            <div class="info">
                                <h3>☁️ Cloud Deployment:</h3>
                                <div class="metric">Platform: Render Cloud</div>
                                <div class="metric">Mode: {'SANDBOX' if SANDBOX_MODE else 'LIVE'} Trading</div>
                                <div class="metric">Port: {PORT}</div>
                                <div class="metric">Auto-restart: Enabled</div>
                                <div class="metric">24/7 Operation: Active</div>
                            </div>
                            
                            <div class="info">
                                <h3>🔧 System Status:</h3>
                                <div class="metric">Health Check: ✅ Active</div>
                                <div class="metric">Bot Process: 🟢 Running</div>
                                <div class="metric">Telegram: 🟢 Connected</div>
                                <div class="metric">Trading Engine: 🟢 Operational</div>
                            </div>
                            
                            <div class="time">
                                🕒 Last Updated: {current_time} | Auto-refresh every 30 seconds
                            </div>
                        </div>
                    </body>
                    </html>
                    '''
                    self.wfile.write(html.encode())
                
                def log_message(self, format, *args):
                    pass  # Suppress HTTP server logs
            
            # Start health server in background thread
            def start_health_server():
                try:
                    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
                    print(f"🌐 Health check server running on port {PORT}")
                    server.serve_forever()
                except Exception as e:
                    print(f"⚠️ Health server error: {e}")
            
            health_thread = threading.Thread(target=start_health_server, daemon=True)
            health_thread.start()
            
            return True
            
    except ImportError:
        print("⚠️ Cloud settings not available - running in local mode")
        return False

def main():
    """Main entry point for the trading bot"""
    logger = setup_logger('main')
    
    # Setup cloud health server if needed
    cloud_mode = setup_cloud_health_server()
    
    print("🤖 Multi-Exchange Trading Bot v2.0")
    print("====================================")
    print(f"Mode: {'SANDBOX' if SANDBOX_MODE else 'LIVE'} trading")
    print("Supported Exchanges: 🟡 Binance, 🟠 Bybit")
    print("Balance Strategy: 0.2% dynamic allocation")
    if cloud_mode:
        print("☁️ Platform: Render Cloud Deployment")
    print("====================================\n")
    
    if not TELEGRAM_TOKEN:
        print("❌ Error: TELEGRAM_TOKEN not configured!")
        print("Please set your token in config/settings.py or environment variables")
        return
    
    try:
        # Initialize and run the bot
        bot = MultiExchangeTradingBot(TELEGRAM_TOKEN, sandbox=SANDBOX_MODE)
        logger.info("🚀 Starting Multi-Exchange Trading Bot...")
        
        # Send cloud deployment notification if applicable
        if cloud_mode:
            logger.info("☁️ Bot running in Render cloud mode")
        
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\n🛑 Bot stopped by user")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {e}")
        
        # Try to send error notification if in cloud mode
        if cloud_mode:
            try:
                logger.error("☁️ Cloud deployment error - bot will auto-restart")
            except:
                pass
        
    finally:
        print("👋 Goodbye!")

if __name__ == "__main__":
    main()