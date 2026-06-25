import os
import requests

from views.view import show_mlflow
from n8n.communicator import ReusableTCPServer, N8nWebhookHandler

PORT = "5000"
WEBHOOK_PORT = 8080


def main():
    print("Init ML App")

    show_mlflow(PORT)

    # Start the webhook listener for n8n in the foreground
    print(f"Listening for n8n triggers on http://localhost:{WEBHOOK_PORT}/api/v1/quality-check")
    with ReusableTCPServer(("0.0.0.0", WEBHOOK_PORT), N8nWebhookHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.server_close()
    

if __name__ == "__main__":
    main()
