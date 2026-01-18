#!/bin/bash
# Deployment script for PythonAnywhere
# Usage: ./deploy.sh

echo "Starting deployment..."

# 1. Pull latest changes
git pull origin main

# 2. Update dependencies
# Assuming virtualenv is named 'venv' and active or available
source venv/bin/activate
pip install -r requirements.txt

# 3. Reload the application
# Touch the wsgi file to trigger reload (standard PA method)
# Replace 'yourusername_pythonanywhere_com_wsgi.py' with your actual WSGI file path if known, 
# or generically:
touch /var/www/*_wsgi.py

echo "Deployment complete! Check your website."
