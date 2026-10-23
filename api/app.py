"""Thin HTTP wrapper around the ClamAV daemon (clamd).

The scanner runs out-of-process: this service only streams the upload to clamd
and maps the result to a small JSON contract:

    {"status": "clean"}                      -> 200
    {"status": "infected", "virus": "..."}   -> 200
    {"status": "error", "message": "..."}    -> 4xx/5xx (client errors / scanner down)
"""

import logging
import os

import pyclamd
from flask import Flask, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge
from waitress import serve

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "550"))
CLAMAV_HOST = os.getenv("CLAMAV_HOST", "clamav")
CLAMAV_PORT = int(os.getenv("CLAMAV_PORT", "3310"))
CLAMAV_TIMEOUT = int(os.getenv("CLAMAV_TIMEOUT", "300"))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


class ScannerUnavailable(RuntimeError):
    """clamd is not reachable or rejected the scan."""


def clamd_client() -> pyclamd.ClamdNetworkSocket:
    try:
        client = pyclamd.ClamdNetworkSocket(
            host=CLAMAV_HOST, port=CLAMAV_PORT, timeout=CLAMAV_TIMEOUT
        )
        if not client.ping():
            raise ScannerUnavailable("clamd did not answer PING")
        return client
    except Exception as exc:  # noqa: BLE001 - surfaced as 503
        raise ScannerUnavailable(str(exc)) from exc


@app.errorhandler(RequestEntityTooLarge)
def handle_too_large(_):
    return jsonify(
        {"status": "error", "message": f"File exceeds {MAX_UPLOAD_MB} MiB"}
    ), 413


@app.route("/scan", methods=["POST"])
def scan_file():
    upload = request.files.get("file")

    if upload is None or upload.filename == "":
        logger.warning("Scan request received without a file part")
        return jsonify({"status": "error", "message": "No file part in the request."}), 400

    try:
        client = clamd_client()
    except ScannerUnavailable as exc:
        logger.error("clamd unavailable: %s", exc)
        return jsonify({"status": "error", "message": "Scanner unavailable"}), 503

    try:
        # scan_stream() uses INSTREAM, so nothing is written to disk here.
        result = client.scan_stream(upload.stream)
    except Exception as exc:  # noqa: BLE001 - includes INSTREAM size limits
        logger.error("Scan failed for %s: %s", upload.filename, exc)
        return jsonify({"status": "error", "message": "Scan failed"}), 503

    if result is None:
        logger.info("Clean: %s", upload.filename)
        return jsonify({"status": "clean"}), 200

    virus = result.get("stream", ("FOUND", "unknown"))[1]
    logger.warning("Infected: %s (%s)", upload.filename, virus)
    return jsonify({"status": "infected", "virus": virus}), 200


@app.route("/health", methods=["GET"])
def health_check():
    try:
        clamd_client()
        return jsonify({"status": "ok", "clamav_connection": "successful"}), 200
    except ScannerUnavailable:
        return jsonify({"status": "error", "clamav_connection": "failed"}), 503


if __name__ == "__main__":
    # Waitress is a production WSGI server; the Flask dev server is single
    # threaded and explicitly not meant for this.
    serve(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5000")),
        threads=int(os.getenv("THREADS", "4")),
    )
