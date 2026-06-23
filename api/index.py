from app.main import app

# Vercel will use this as the entry point for serverless functions
# The FastAPI app is already configured in app/main.py
app_handler = app

# For Vercel serverless deployment
from mangum import Mangum

handler = Mangum(app)
