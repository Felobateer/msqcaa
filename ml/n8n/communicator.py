import os
import requests
import json
import http.server
import socketserver
from dataclasses import dataclass

from model.models import check_quality, run_inference

@dataclass
class SampleData:
    id: int
    temperature: float
    pressure: float
    ph_level: float

def notify_automation_tools(sample_id: int, prediction: int):
    n8n_webhook_url = os.getenv("N8N_URL")

    payload = {
        "sample_id": sample_id,
        "prediction": prediction,
        "status": "completed"
    }

    try:
        requests.post(n8n_webhook_url, json=payload, timeout=5)
        print(f"Successfully notified automation for sample {sample_id}")
    except requests.exceptions.RequestException as e:
        print(f"Webhook failed: {e}")

class N8nWebhookHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/v1/quality-check':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            try:
                # parse json sent by n8n
                payload = json.loads(post_data.decode('utf-8'))

                # Convert it to an object so data.id, data.temperature works
                sample = SampleData(
                    id=payload['id'],
                    temperature=payload['temperature'],
                    pressure=payload['pressure'],
                    ph_level=payload['ph_level']
                )
                
                # Run your ML model
                prediction = check_quality("latest", sample)
                
                # Send the success response back to n8n immediately
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                response = {
                    "status": "success",
                    "sample_id": sample.id,
                    "prediction": prediction
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))
                
            except Exception as e:
                # Tell n8n if something crashed
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {"status": "error", "message": str(e)}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True