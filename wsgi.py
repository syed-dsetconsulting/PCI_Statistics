#!/usr/bin/python3.10

import sys
import os

# Add your project directory to the Python path
path = '/home/yourusername/PCI_Statistics'  # Replace 'yourusername' with your PythonAnywhere username
if path not in sys.path:
    sys.path.append(path)

# Import your Flask/Dash app
from main import app

# This is the WSGI entry point
application = app.server

if __name__ == "__main__":
    application.run()
