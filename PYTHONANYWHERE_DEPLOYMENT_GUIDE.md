# Deploying GOST Tunnel Manager to PythonAnywhere

This guide outlines the steps to deploy the GOST Tunnel Manager Flask application to PythonAnywhere.

## 1. Account Setup

*   **Sign Up:** If you don't have an account, sign up at [www.pythonanywhere.com](https://www.pythonanywhere.com). The free tier ("Beginner" account) should be sufficient for this application, keeping in mind its limitations.

## 2. Upload Application Files

You have a couple of options:

*   **Option A: Git Clone (Recommended if your code is in a Git repository)**
    1.  Open a **Bash Console** from your PythonAnywhere dashboard.
    2.  Clone your repository:
        ```bash
        git clone <your_repository_url> YourProjectDirName
        cd YourProjectDirName
        ```
        Replace `<your_repository_url>` with the URL of your Git repo and `YourProjectDirName` with your desired directory name (e.g., `gost-tunnel-manager`).

*   **Option B: Upload ZIP File**
    1.  Create a ZIP file of your project directory (ensure it includes `app.py`, `models.py`, `utils.py`, `gost_config_generator.py`, `requirements.txt`, `wsgi_template.py`, and the `templates`, `static`, `translations` folders).
    2.  Go to the **Files** tab on PythonAnywhere.
    3.  Navigate to the directory where you want to upload your project (e.g., create a new directory like `gost-tunnel-manager`).
    4.  Use the **Upload a file** button. Note that PythonAnywhere's free tier has limits on file size. For larger projects, `git` is preferred.
    5.  If you upload a ZIP, you'll need to unzip it in a Bash Console:
        ```bash
        unzip your_project_files.zip -d YourProjectDirName
        cd YourProjectDirName
        ```

## 3. Virtual Environment Setup

It's crucial to use a virtual environment.

1.  In your Bash Console, navigate into your project directory:
    ```bash
    cd /home/YourUserName/YourProjectDirName 
    # Replace YourUserName and YourProjectDirName accordingly
    ```
2.  Create a virtual environment. Choose a Python version supported by your code (e.g., Python 3.10):
    ```bash
    mkvirtualenv --python=/usr/bin/python3.10 myenv 
    # 'myenv' can be any name for your virtual environment
    ```
    Your console prompt should change to indicate you're in the virtual environment (e.g., `(myenv) $`).
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## 4. Web App Configuration

1.  Go to the **Web** tab on your PythonAnywhere dashboard.
2.  Click **Add a new web app**.
    *   Confirm your domain name (e.g., `YourUserName.pythonanywhere.com`).
    *   Choose **Manual configuration (including virtualenvs)**.
    *   Select the Python version you used for your virtual environment (e.g., Python 3.10).
    *   PythonAnywhere will create your web app and take you to the configuration page.

3.  **Virtualenv:**
    *   Scroll to the "Virtualenv" section.
    *   Enter the path to your virtual environment: `/home/YourUserName/.virtualenvs/myenv` (replace `YourUserName` and `myenv` if you used different names).

4.  **Code (Paths):**
    *   **Source code:** Set this to your project's main directory: `/home/YourUserName/YourProjectDirName`
    *   **Working directory:** Set this to the same path: `/home/YourUserName/YourProjectDirName`

5.  **WSGI Configuration File:**
    *   Scroll to the "Code" section. Click on the "WSGI configuration file" link (it will likely be `/var/www/YourUserName_pythonanywhere_com_wsgi.py` or similar).
    *   Edit this file. Delete the default content and replace it with the content from your `wsgi_template.py` file, making necessary modifications.

    *   **Key modifications for your WSGI file:**
        *   Change `project_home = u'/home/YourUserName/YourProjectDirName'` to your actual project path.
        *   Ensure `from app import app as application` correctly points to your Flask app instance.
        *   The `instance` folder should be created automatically by `app.py` if `os.makedirs(app.instance_path)` is present and the app has permissions. The default SQLite DB and `gost_config.json` will be stored here.

        **Example `wsgi.py` content (adapted from `wsgi_template.py`):**
        ```python
        import sys
        import os

        # Path to your project directory on PythonAnywhere
        project_home = u'/home/YourUserName/YourProjectDirName' 
        if project_home not in sys.path:
            sys.path = [project_home] + sys.path

        # Set environment variables (FERNET_KEY is best set via the Web tab UI)
        # os.environ['FLASK_APP'] = 'app.py' # Not strictly needed for WSGI but good for flask commands
        # os.environ['FLASK_ENV'] = 'production' 

        from app import app as application

        # Optional: Initialize DB if not handled elsewhere and safe for production
        # with application.app_context():
        #    from app import init_db
        #    init_db() 
        ```

## 5. Static Files Configuration

1.  On the **Web** tab, scroll to the "Static files" section.
2.  Click **Add a new static file mapping**.
    *   **URL:** `/static`
    *   **Directory:** `/home/YourUserName/YourProjectDirName/static` (replace with your actual path)

## 6. Environment Variables

1.  On the **Web** tab, scroll to the "Environment variables" section.
2.  Add the following environment variables:
    *   `FERNET_ENCRYPTION_KEY`: Paste the **production** Fernet key you generated. **This is crucial for security.**
    *   `FLASK_APP` (optional, but good practice): `app.py`
    *   `FLASK_ENV` (optional): `production` (or `development` for debugging, but switch to `production` for live).
    *   `DATABASE_URL` (optional): If you decide to use a more robust database like PostgreSQL or MySQL provided by PythonAnywhere (paid feature), you'd set its connection string here. Otherwise, the app defaults to SQLite in the instance folder.

## 7. Database

*   The application is configured to use SQLite. The database file (`default.db`) will be automatically created inside an `instance` folder within your project's working directory (e.g., `/home/YourUserName/YourProjectDirName/instance/default.db`) when the app first tries to access the database.
*   The `instance` folder creation is handled by `app.py`.

## 8. Reloading the Web App

*   After making any changes to your code, WSGI file, or environment variables, go to the **Web** tab and click the **Reload YourUserName.pythonanywhere.com** button (the green button).
*   Wait a few moments for the app to reload.

## 9. Accessing Logs

*   **Error Log:** Found in the "Log files" section on the **Web** tab. This log (`error.log`) shows Python errors and tracebacks.
*   **Server Log:** Also in "Log files". This log (`server.log`) shows requests made to your app, status codes, etc.
*   **Access Log:** Shows web server access details.
*   Check these logs first if your application isn't working as expected.

## 10. GOST Limitations on PythonAnywhere (Crucial)

The GOST Tunnel Manager application is designed to generate GOST configuration files and can attempt to control a local GOST service using `systemctl`. However, on PythonAnywhere (especially the free tier), you **do not have `sudo` access** and cannot run system-wide services like `gost.service` via `systemctl`.

*   **`sudo systemctl` Commands Will Fail:** The parts of the application that try to run `sudo systemctl restart gost.service` (or `start`, `stop`) will fail. The application is designed to catch these errors and display a message.
*   **`gost_config.json` Path:** The application has been modified to save `gost_config.json` into its `instance` folder (e.g., `/home/YourUserName/YourProjectDirName/instance/gost_config.json`).
*   **Running GOST Manually:**
    1.  You would need to **manually install GOST** in your PythonAnywhere account (e.g., download the binary to your home directory).
    2.  You must run GOST as a **user process**. You can do this from a Bash console.
    3.  You need to configure your manually run GOST instance to use the `gost_config.json` file generated by this web application. For example:
        ```bash
        # In a PythonAnywhere Bash console
        /path/to/your/gost -C /home/YourUserName/YourProjectDirName/instance/gost_config.json
        ```
    4.  **Process Management:**
        *   To keep GOST running after you close the console, you might use `nohup ... &` or explore PythonAnywhere's "Always-on tasks" (a paid feature, but might be scriptable for checking/restarting GOST if the config changes).
        *   The "Apply Config & Restart GOST" button in the web app will generate the `gost_config.json` file in the instance folder. However, the "Restart GOST" part will fail, and an error message about this will be displayed by the web app. You will need to manually restart your GOST process if it's already running to pick up the new configuration.

**In summary for GOST:** The web application can manage the *configuration* of GOST, but you are responsible for running and managing the GOST *process* itself on PythonAnywhere.

## 11. First Run & Database Initialization
*   After deploying and reloading the web app, the first time you access a page that uses the database, the `init_db()` function (called via `app.py` or your WSGI setup) should create the SQLite database file in the `instance` folder.

By following these steps, you should be able to get your GOST Tunnel Manager application running on PythonAnywhere. Remember to consult the PythonAnywhere help pages for more detailed information on specific features.
