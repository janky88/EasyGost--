import sys
import os

# Add your project's directory to the Python path.
# Replace '/home/YourUserName/YourProjectDirName' with the actual path to your project directory on PythonAnywhere.
project_home = u'/home/YourUserName/YourProjectDirName' 
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Set environment variables if necessary (e.g., for FERNET_KEY or other configurations)
# os.environ['FERNET_KEY'] = 'your_production_fernet_key_here' # Best set via PythonAnywhere's web UI
# os.environ['DATABASE_URL'] = 'your_production_database_url_here' # If using a different DB in prod

# Import the Flask app instance.
# Ensure 'app.py' (or your main Flask file) is in the project_home directory specified above.
from app import app as application  # The 'application' variable is what PythonAnywhere's WSGI server looks for.

# Optional: If your app uses an instance folder for configuration or SQLite DB,
# ensure PythonAnywhere knows where it is if it's not automatically detected.
# application.instance_path = os.path.join(project_home, 'instance')
# if not os.path.exists(application.instance_path):
#    os.makedirs(application.instance_path)

# Optional: Initialize database if it needs to happen on app load and is safe to do so.
# with application.app_context():
#    from app import init_db
#    init_db() # Or a more specific production init function

# Optional: Add any other production-specific setup here.
# For example, logging configuration.
# import logging
# if not application.debug:
#    stream_handler = logging.StreamHandler()
#    stream_handler.setLevel(logging.INFO)
#    application.logger.addHandler(stream_handler)
