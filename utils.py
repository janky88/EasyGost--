from cryptography.fernet import Fernet, InvalidToken
import paramiko
import socket # For socket.error

def generate_key():
    """Generates a Fernet key."""
    return Fernet.generate_key()

def encrypt_password(password, key):
    """Encrypts a password using the given Fernet key."""
    if not password:
        return None
    f = Fernet(key)
    return f.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password, key):
    """Decrypts an encrypted password using the given Fernet key."""
    if not encrypted_password:
        return None
    f = Fernet(key)
    try:
        return f.decrypt(encrypted_password.encode()).decode()
    except InvalidToken:
        # This can happen if the key is wrong or the token is corrupted
        print("Error: Invalid token or key during decryption.")
        return None

def test_ssh_connection(ip, port, username, password):
    """
    Tests an SSH connection to the given server details.
    Returns (True, None) on success, or (False, error_message) on failure.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # Automatically add host keys

    try:
        # Ensure port is an integer
        port = int(port)
        if not password: # paramiko might hang or error weirdly with None password
            return False, "Password cannot be empty for SSH test."
            
        client.connect(ip, port=port, username=username, password=password, timeout=10)
        return True, None
    except paramiko.AuthenticationException:
        return False, "Authentication failed (wrong username or password)."
    except paramiko.SSHException as e:
        return False, f"SSH error: {str(e)}"
    except socket.error as e: # More specific network errors
        return False, f"Network error: {str(e)}"
    except TimeoutError: # Python's built-in TimeoutError
         return False, f"Connection timed out to {ip}:{port}."
    except Exception as e:
        return False, f"An unexpected error occurred: {str(e)}"
    finally:
        client.close()

import subprocess
from flask_babel import gettext as _ # Import gettext

def _run_systemctl_command(action, service_name="gost.service"):
    """
    Helper function to run systemctl commands.
    Returns (success: bool, output: str).
    Note: This will likely require sudo privileges for the user running the Flask app.
    """
    try:
        # Using 'sudo' directly here. If passwordless sudo is not configured for the
        # user running the app, this will fail or hang if sudo prompts for a password.
        # In a production environment, more robust IPC or a dedicated service manager agent
        # would be used.
        command = ['sudo', 'systemctl', action, service_name]
        process = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False)
        
        if process.returncode == 0:
            return True, process.stdout.strip() or _("%(action)s %(service_name)s successful.", action=action, service_name=service_name)
        else:
            error_message = process.stderr.strip() or process.stdout.strip() or _("Unknown error during %(action)s %(service_name)s.", action=action, service_name=service_name)
            # Log the full command and error for debugging
            print(f"Error running command '{' '.join(command)}': {error_message}")
            print(f"Stdout: {process.stdout.strip()}")
            print(f"Stderr: {process.stderr.strip()}")
            return False, error_message
            
    except FileNotFoundError:
        print(_("Error: 'sudo' or 'systemctl' command not found. Make sure it's in PATH."))
        return False, _("'sudo' or 'systemctl' command not found.")
    except subprocess.TimeoutExpired:
        print(_("Error: Command '%(command)s' timed out.", command=' '.join(command)))
        return False, _("Command to %(action)s %(service_name)s timed out.", action=action, service_name=service_name)
    except Exception as e:
        print(_("An unexpected error occurred while trying to %(action)s %(service_name)s: %(error)s", action=action, service_name=service_name, error=str(e)))
        return False, _("An unexpected error occurred: %(error)s", error=str(e))

def restart_gost_service():
    """Restarts the GOST service. Returns (success, message)."""
    return _run_systemctl_command('restart')

def stop_gost_service():
    """Stops the GOST service. Returns (success, message)."""
    return _run_systemctl_command('stop')

def start_gost_service():
    """Starts the GOST service. Returns (success, message)."""
    return _run_systemctl_command('start')

def get_gost_service_status():
    """Gets the GOST service status. Returns (success, message)."""
    # 'is-active' is a simple way to check if it's running.
    # For more detailed status, 'status' can be used, but parsing its output is more complex.
    return _run_systemctl_command('is-active')
