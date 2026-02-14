from fastapi import FastAPI
import sys
import os

# Add backend directory to Python path so we can import 'main'
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))

# Import the FastAPI application
from main import app

# Vercel expects the WSGI/ASGI application to be exposed as a variable named 'app'
# This handles the routing for /api/*
