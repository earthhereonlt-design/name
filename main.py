import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def start_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    print(f"Starting dummy web server on port {port} for health checks...")
    server.serve_forever()

def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        print("TELEGRAM_TOKEN not found in environment variables.")
        print("Please set TELEGRAM_TOKEN and GEMINI_API_KEY before running.")
        sys.exit(1)
        
    # Start the dummy web server in a background thread
    threading.Thread(target=start_dummy_server, daemon=True).start()
        
    print("Starting Telegram Bot...")
    from bot import build_app
    app = build_app()
    app.run_polling()

if __name__ == "__main__":
    main()
