import json
import os
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlsplit


APP_DATA = Path(
    os.environ.get(
        "LOCALAPPDATA",
        str(Path.home() / ".local" / "share"),
    )
) / "BirthdayWeb"
MESSAGES_FILE = APP_DATA / "messages.json"
MESSAGES_LOCK = Lock()
MAX_REQUEST_BYTES = 4096
MAX_NAME_LENGTH = 40
MAX_MESSAGE_LENGTH = 500


class BirthdayRequestHandler(SimpleHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def read_messages(self):
        if not MESSAGES_FILE.exists():
            return []
        with MESSAGES_FILE.open("r", encoding="utf-8") as messages_file:
            messages = json.load(messages_file)
        if not isinstance(messages, list):
            raise ValueError("Saved messages must be a list.")
        return messages

    def do_GET(self):
        parsed_path = urlsplit(self.path)
        if parsed_path.path == "/":
            self.send_response(302)
            self.send_header("Location", "/FinalHBD.html")
            self.end_headers()
            return
        if parsed_path.path != "/api/messages":
            return super().do_GET()
        try:
            with MESSAGES_LOCK:
                messages = self.read_messages()
            if parse_qs(parsed_path.query).get("source") == ["FinalHBD"]:
                messages = [
                    message for message in messages
                    if message.get("source") == "FinalHBD"
                ]
        except (OSError, json.JSONDecodeError, ValueError) as error:
            self.log_error("Could not read saved messages: %s", error)
            self.send_json(500, {"error": "Could not load saved wishes."})
            return
        self.send_json(200, {"messages": messages})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/messages":
            self.send_error(404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self.send_json(400, {"error": "Invalid request size."})
            return
        if content_length < 1 or content_length > MAX_REQUEST_BYTES:
            self.send_json(413, {"error": "Request is empty or too large."})
            return

        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"error": "Request must contain valid JSON."})
            return
        if not isinstance(payload, dict):
            self.send_json(400, {"error": "Request must be a JSON object."})
            return

        name = payload.get("name")
        message = payload.get("message")
        source = payload.get("source")
        if not isinstance(name, str) or not isinstance(message, str):
            self.send_json(400, {"error": "Name and wish must be text."})
            return
        if source != "FinalHBD":
            self.send_json(400, {"error": "Wishes must be submitted from FinalHBD."})
            return
        name = name.strip()
        message = message.strip()
        if not name or not message:
            self.send_json(400, {"error": "Please enter your name and wish."})
            return
        if len(name) > MAX_NAME_LENGTH or len(message) > MAX_MESSAGE_LENGTH:
            self.send_json(400, {"error": "Name or wish exceeds the character limit."})
            return

        new_message = {
            "name": name,
            "message": message,
            "source": source,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        try:
            with MESSAGES_LOCK:
                messages = self.read_messages()
                messages.append(new_message)
                APP_DATA.mkdir(parents=True, exist_ok=True)
                temporary_file = MESSAGES_FILE.with_suffix(".tmp")
                temporary_file.write_text(
                    json.dumps(messages, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                temporary_file.replace(MESSAGES_FILE)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            self.log_error("Could not save wish: %s", error)
            self.send_json(500, {"error": "Could not save your wish. Please try again."})
            return
        self.send_json(201, {"message": new_message})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), BirthdayRequestHandler)
    print("Birthday website running at http://localhost:8000/")
    print("Stop the server with Ctrl+C.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBirthday website server stopped.")
    finally:
        server.server_close()
