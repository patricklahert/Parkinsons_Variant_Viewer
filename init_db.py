from src.parkinsons_variant_viewer.web import create_app
from src.parkinsons_variant_viewer.web.db import init_db

app = create_app()

with app.app_context():
    init_db()

print("Database initialized.")