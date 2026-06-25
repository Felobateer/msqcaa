import os
import subprocess
from utils.db import mlflow_db_url


def show_mlflow(PORT):
    env = os.environ.copy()
    env["MLFLOW_TRACKING_URI"] = mlflow_db_url

    subprocess.Popen(["uv", "run", "mlflow", "server",
                    "--backend-store-uri", mlflow_db_url,
                    "--host", "0.0.0.0",
                    "--port", PORT],
                    env=env)
    
    print(f"MLflow UI live at http://localhost:{PORT}")