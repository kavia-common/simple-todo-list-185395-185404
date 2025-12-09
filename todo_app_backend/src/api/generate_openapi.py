import json
import os

from src.api.main import app

# Generate and write the OpenAPI schema to the interfaces directory
openapi_schema = app.openapi()
output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "interfaces")
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "openapi.json")

with open(output_path, "w") as f:
    json.dump(openapi_schema, f, indent=2)
