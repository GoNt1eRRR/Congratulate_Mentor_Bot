import socketserver
import json
import argparse
from http.server import SimpleHTTPRequestHandler

PORT = 8000

parser = argparse.ArgumentParser(description='Simple HTTP Server with JSON endpoint')
parser.add_argument('--file', type=str, required=True, help='Path to the JSON file')
args = parser.parse_args()

JSON_FILE = args.file


class RequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        try:
            with open(JSON_FILE, 'r', encoding='utf-8') as file:
                data = file.read()

            try:
                json.loads(data)
                valid_json = True
            except json.JSONDecodeError:
                valid_json = False

            if valid_json:
                json_data = json.loads(data)

                if self.path == '/':
                    response = json_data
                elif self.path == '/mentors':
                    response = json_data.get('mentors', {})
                elif self.path == '/postcards':
                    response = json_data.get('postcards', {})
                else:
                    response = {}

                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(response, ensure_ascii=False, indent=4).encode('utf-8'))

            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(data.encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            error_message = {"error": f"Ошибка сервера: {str(e)}"}
            self.wfile.write(json.dumps(error_message, ensure_ascii=False, indent=4).encode('utf-8'))


with socketserver.TCPServer(("", PORT), RequestHandler) as httpd:
    print(f"🚀 Сервер запущен на порту {PORT}, ссылка - http://127.0.0.1:8000")
    httpd.serve_forever()
