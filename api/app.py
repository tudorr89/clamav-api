import os
import logging
from flask import Flask, request, jsonify
import pyclamd

# --- Configuration & Initialization ---

# Configure basic logging to see detailed output in the container logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize the Flask application
app = Flask(__name__)

# --- ClamAV Connection ---

# The ClamAV daemon (clamd) service name as defined in docker-compose.yml
CLAMAV_HOST = 'clamav'
CLAMAV_PORT = 3310

def get_clamd_socket():
    """
    Initializes and returns a connection to the ClamAV daemon.
    This function specifically uses a NETWORK socket.
    """
    try:
        # Explicitly log the connection attempt details. This is key for debugging.
        logging.info(f"Attempting to connect to ClamAV via NETWORK socket at {CLAMAV_HOST}:{CLAMAV_PORT}")

        # Create a network socket connection to the clamd daemon.
        # This is the correct method for a multi-container Docker setup.
        cd = pyclamd.ClamdNetworkSocket(host=CLAMAV_HOST, port=CLAMAV_PORT)

        # Ping the server to ensure the connection is alive.
        # This will raise a ConnectionError if it fails, which will be caught.
        cd.ping()

        logging.info("Successfully connected and pinged the ClamAV daemon.")
        return cd

    except Exception as e:
        # Log the specific error, which is crucial for troubleshooting.
        logging.error(f"Failed to connect to ClamAV daemon at {CLAMAV_HOST}:{CLAMAV_PORT}. Error: {e}")
        logging.error("This usually means the 'clamav' container is not running, not healthy, or not reachable on the Docker network.")
        logging.error("Please check the clamav container's status and logs with: docker-compose logs -f clamav")
        return None

# --- API Endpoints ---

@app.route('/scan', methods=['POST'])
def scan_file():
    """
    Handles file uploads and scans them for viruses.
    """
    # 1. Validate the incoming request
    if 'file' not in request.files:
        logging.warning("Scan request received with no file part.")
        return jsonify({"status": "error", "message": "No file part in the request."}), 400

    file = request.files['file']

    if file.filename == '':
        logging.warning("Scan request received with an empty filename.")
        return jsonify({"status": "error", "message": "No file selected for uploading."}), 400

    # 2. Connect to the ClamAV daemon
    clamd_socket = get_clamd_socket()
    if not clamd_socket:
        # The error is already logged in get_clamd_socket()
        return jsonify({"status": "error", "message": "Could not connect to the scanner service. Check API logs for details."}), 503

    # 3. Scan the file stream
    try:
        logging.info(f"Scanning file: {file.filename}")
        # The scan_stream method is efficient as it scans the file in chunks
        # without saving it to disk on the API server.
        scan_result = clamd_socket.scan_stream(file.stream)

        # 4. Process the scan result
        if scan_result is None:
            # No virus found
            logging.info(f"File is clean: {file.filename}")
            return jsonify({"status": "clean", "message": "File is clean."}), 200
        else:
            # Virus found
            virus_name = scan_result['stream'][1]
            logging.warning(f"Infected file detected: {file.filename}, Virus: {virus_name}")
            return jsonify({
                "status": "infected",
                "message": "File is infected!",
                "virus": virus_name
            }), 200

    except Exception as e:
        logging.error(f"An error occurred during scanning: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred during the scan."}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """
    A simple health check endpoint to verify service status.
    """
    clamd_socket = get_clamd_socket()
    if clamd_socket:
        return jsonify({"status": "ok", "clamav_connection": "successful"}), 200
    else:
        return jsonify({"status": "error", "clamav_connection": "failed"}), 503

# --- Main Execution ---

if __name__ == '__main__':
    # Run the Flask app
    # host='0.0.0.0' makes the server accessible from other Docker containers
    # and the host machine.
    app.run(host='0.0.0.0', port=5000, debug=False)
