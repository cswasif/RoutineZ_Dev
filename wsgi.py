from api.f import app
from waitress import serve
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Create logger for Waitress
logger = logging.getLogger('waitress')
logger.setLevel(logging.DEBUG)

# Enable Flask debug logging
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    print("\n=== Starting Production Server with Debug Logging ===")
    print("Server URL: http://0.0.0.0:5000")
    print("Debug logging enabled")
    print("Press Ctrl+C to stop the server\n")
    serve(
        app,
        host='0.0.0.0',
        port=5000,
        threads=4,
        log_socket_errors=True,
        clear_untrusted_proxy_headers=True
    ) 