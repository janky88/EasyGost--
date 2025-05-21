from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel, gettext as _ # Import gettext as _
import os
import json # For writing the gost config
from cryptography.fernet import Fernet # For key generation
import subprocess # For sudo mv in apply_gost_config

# Assuming utils.py is in the same directory
from utils import generate_key, encrypt_password, test_ssh_connection, \
                  restart_gost_service, stop_gost_service, start_gost_service, \
                  get_gost_service_status
                  
from gost_config_generator import generate_gost_config


# models.py should import db from this app.py
# from models import Servers # This will be imported after db is initialized

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# Configure Flask-Babel
app.config['BABEL_DEFAULT_LOCALE'] = 'zh'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
babel = Babel(app)

# Using default locale 'zh' as per config. No localeselector needed for now.

# Fernet Key for password encryption
# Attempt to load from environment variable, otherwise use a default (for dev/test)
# In production, FERNET_ENCRYPTION_KEY MUST be set as an environment variable.
DEFAULT_FERNET_KEY_FOR_DEV = b'jG5FCcuiEW8ORq4T7eO_yFA9hDUiTbjGZXNv7SdOwJk=' # Default for dev if not set
FERNET_KEY_ENV_VAR = 'FERNET_ENCRYPTION_KEY'
env_fernet_key = os.environ.get(FERNET_KEY_ENV_VAR)

if env_fernet_key:
    app.config['FERNET_KEY'] = env_fernet_key.encode()
    print(f"Info: Loaded Fernet key from environment variable {FERNET_KEY_ENV_VAR}.")
else:
    print(f"Warning: Environment variable {FERNET_KEY_ENV_VAR} not set. "
          f"Using a default Fernet key for development/testing. "
          f"Ensure {FERNET_KEY_ENV_VAR} is set in a production environment.")
    app.config['FERNET_KEY'] = DEFAULT_FERNET_KEY_FOR_DEV
    # For a stricter production setup, you might raise an error here if the key isn't set:
    # else:
    #     raise EnvironmentError(f"FATAL: Environment variable {FERNET_KEY_ENV_VAR} is not set. "
    #                            "This is required for production.")

# Ensure instance folder exists for SQLite DB, config files, etc.
try:
    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)
    print(f"Info: Instance path is {app.instance_path}")
except OSError as e:
    print(f"Error creating instance path {app.instance_path}: {e}")
    # Depending on severity, might want to exit or log more formally


# Configure the SQLAlchemy part of the app instance
# Update SQLite path to be in the instance folder for better organization
default_db_path = os.path.join(app.instance_path, 'default.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{default_db_path}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create the SQLAlchemy db instance
db = SQLAlchemy(app)

# Now that db is initialized, we can import models
import models # This will now work if models.py uses `from app import db`

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    with app.app_context():
        db.create_all()

@app.route('/')
def hello_world():
    return 'Hello, World! Navigation: <a href="/add_server">Add Server</a> | <a href="/list_servers">List Servers</a> | <a href="/add_transit">Add Transit</a> | <a href="/list_transits">List Transits</a> | <a href="/status">System Status</a>'

@app.route('/add_server', methods=['GET', 'POST'])
def add_server():
    if request.method == 'POST':
        server_name = request.form.get('server_name')
        ip_address = request.form.get('ip_address')
        ssh_username = request.form.get('ssh_username')
        ssh_password = request.form.get('ssh_password') # Raw password from form
        try:
            ssh_port = int(request.form.get('ssh_port', '22'))
        except ValueError:
            flash(_('SSH Port must be a number.'), 'error')
            return redirect(url_for('add_server'))

        if not all([server_name, ip_address, ssh_username, ssh_password]): # ssh_port has a default
            flash(_('All fields (Server Name, IP, Username, Password) are required!'), 'error')
            return redirect(url_for('add_server'))
        
        # Check for duplicate server name or IP
        existing_server_name = models.Servers.query.filter_by(name=server_name).first()
        if existing_server_name:
            flash(_("Server name '%(server_name)s' already exists.", server_name=server_name), 'error')
            return redirect(url_for('add_server'))
        
        existing_server_ip = models.Servers.query.filter_by(ip_address=ip_address).first()
        if existing_server_ip:
            flash(_("IP address '%(ip_address)s' already exists for server '%(server_name)s'.", ip_address=ip_address, server_name=existing_server_ip.name), 'error')
            return redirect(url_for('add_server'))

        # Test SSH connection
        # We use the raw password for the test
        conn_test_success, conn_test_msg = test_ssh_connection(ip_address, ssh_port, ssh_username, ssh_password)

        if conn_test_success:
            encrypted_password = encrypt_password(ssh_password, app.config['FERNET_KEY'])
            
            new_server = models.Servers(
                name=server_name,
                ip_address=ip_address,
                ssh_username=ssh_username,
                ssh_password=encrypted_password,
                ssh_port=ssh_port,
                connection_status='Connected'
            )
            try:
                db.session.add(new_server)
                db.session.commit()
                flash(_("Server '%(server_name)s' added successfully and connection verified!", server_name=server_name), 'success')
            except Exception as e:
                db.session.rollback()
                flash(_("Error saving server to database: %(error)s", error=str(e)), 'error')
        else:
            # Do not save if SSH connection test fails
            flash(_("Could not connect to server '%(server_name)s': %(conn_test_msg)s", server_name=server_name, conn_test_msg=conn_test_msg), 'error')
        
        return redirect(url_for('add_server'))

    return render_template('add_server.html')

@app.route('/list_servers')
def list_servers():
    # This is a simple listing, you might want pagination for many servers
    servers = models.Servers.query.all()
    return render_template('list_servers.html', servers=servers)

@app.route('/add_transit', methods=['GET', 'POST'])
def add_transit():
    if request.method == 'POST':
        transit_name = request.form.get('transit_name')
        server_a_id = request.form.get('server_a_id')
        server_a_listen_port = request.form.get('server_a_listen_port')
        server_b_id = request.form.get('server_b_id')
        server_b_connect_port = request.form.get('server_b_connect_port')
        encryption_protocol = request.form.get('encryption_protocol')
        destination_ip = request.form.get('destination_ip')
        destination_port = request.form.get('destination_port')

        # Basic validation
        if not all([transit_name, server_a_id, server_a_listen_port, server_b_id, server_b_connect_port, encryption_protocol, destination_ip, destination_port]):
            flash(_('All fields are required!'), 'error')
            # Need to pass servers again if we redirect to GET, or just render_template
            servers_for_dropdown = models.Servers.query.order_by(models.Servers.name).all()
            return render_template('add_transit.html', servers=servers_for_dropdown, current_data=request.form) # Pass current_data

        if server_a_id == server_b_id:
            flash(_('Server A and Server B cannot be the same server.'), 'error')
            servers_for_dropdown = models.Servers.query.order_by(models.Servers.name).all()
            return render_template('add_transit.html', servers=servers_for_dropdown, current_data=request.form)

        # Validate port numbers
        try:
            server_a_listen_port_int = int(server_a_listen_port)
            server_b_connect_port_int = int(server_b_connect_port)
            destination_port_int = int(destination_port)
            ports_to_check = {
                _("Server A Listen Port"): server_a_listen_port_int,
                _("Server B Connect Port"): server_b_connect_port_int,
                _("Destination Port"): destination_port_int
            }
            for port_name, port_val in ports_to_check.items():
                if not (1 <= port_val <= 65535):
                    flash(_("%(port_name)s must be between 1 and 65535.", port_name=port_name), 'error')
                    servers_for_dropdown = models.Servers.query.order_by(models.Servers.name).all()
                    return render_template('add_transit.html', servers=servers_for_dropdown, current_data=request.form)
        except ValueError:
            flash(_('All port numbers must be valid integers.'), 'error')
            servers_for_dropdown = models.Servers.query.order_by(models.Servers.name).all()
            return render_template('add_transit.html', servers=servers_for_dropdown, current_data=request.form)

        # Validate Server A and Server B exist
        server_a = models.Servers.query.get(server_a_id)
        server_b = models.Servers.query.get(server_b_id)

        if not server_a:
            flash(_("Selected Server A (ID: %(server_id)s) does not exist.", server_id=server_a_id), 'error')
            servers_for_dropdown = models.Servers.query.order_by(models.Servers.name).all()
            return render_template('add_transit.html', servers=servers_for_dropdown, current_data=request.form)
        if not server_b:
            flash(_("Selected Server B (ID: %(server_id)s) does not exist.", server_id=server_b_id), 'error')
            servers_for_dropdown = models.Servers.query.order_by(models.Servers.name).all()
            return render_template('add_transit.html', servers=servers_for_dropdown, current_data=request.form)
            
        # Check for duplicate transit name
        existing_transit_name = models.Transits.query.filter_by(name=transit_name).first()
        if existing_transit_name:
            flash(_("Transit name '%(transit_name)s' already exists.", transit_name=transit_name), 'error')
            servers_for_dropdown = models.Servers.query.order_by(models.Servers.name).all()
            return render_template('add_transit.html', servers=servers_for_dropdown, current_data=request.form)

        # Optional: Check for port conflicts on Server A
        # existing_listen_port_on_server_a = models.Transits.query.filter_by(server_a_id=server_a_id, server_a_listen_port=server_a_listen_port_int).first()
        # if existing_listen_port_on_server_a:
        #     flash(_("Port %(port)s is already in use for a transit on Server A (%(server_name)s).", port=server_a_listen_port_int, server_name=server_a.name), 'error')
        #     servers_for_dropdown = models.Servers.query.order_by(models.Servers.name).all()
        #     return render_template('add_transit.html', servers=servers_for_dropdown, current_data=request.form)

        new_transit = models.Transits(
            name=transit_name,
            server_a_id=int(server_a_id),
            server_a_listen_port=server_a_listen_port_int,
            server_b_id=int(server_b_id),
            server_b_connect_port=server_b_connect_port_int,
            encryption_protocol=encryption_protocol,
            destination_ip=destination_ip,
            destination_port=destination_port_int,
            status='pending' # Initial status
        )
        
        try:
            db.session.add(new_transit)
            db.session.commit()
            flash(_("Transit configuration '%(transit_name)s' added successfully with status 'pending'.", transit_name=transit_name), 'success')
            return redirect(url_for('list_transits')) # Redirect to list view after success
        except Exception as e:
            db.session.rollback()
            flash(_("Error saving transit configuration to database: %(error)s", error=str(e)), 'error')
            servers_for_dropdown = models.Servers.query.order_by(models.Servers.name).all()
            return render_template('add_transit.html', servers=servers_for_dropdown, current_data=request.form)

    # GET request
    servers_for_dropdown = models.Servers.query.order_by(models.Servers.name).all()
    if not servers_for_dropdown:
        flash(_('No servers found. Please add at least two servers before creating a transit.'), 'error')
        # Optionally redirect to add_server page or just show the form disabled/with message
        # return redirect(url_for('add_server'))
    # Pass current_data as None for GET requests or if not set by a POST error
    return render_template('add_transit.html', servers=servers_for_dropdown, current_data=None)

# Template context processor to inject 'now' for footer year
import datetime
@app.context_processor
def inject_now():
    return {'now': datetime.datetime.utcnow}

@app.route('/apply_gost_config', methods=['POST'])
def apply_gost_config():
    # 1. Fetch 'active' and 'pending' transits
    # We'll generate config for all transits marked 'pending' or 'active'.
    # If a transit is 'error' or 'inactive' it won't be part of the new config.
    # However, the current generate_gost_config takes all transits passed to it.
    # So, we select them here.
    transits_to_configure = models.Transits.query.filter(
        models.Transits.status.in_(['pending', 'active', 'error']) # Include 'error' to try and fix them
    ).all()

    all_servers = models.Servers.query.all()
    servers_map = {server.id: server for server in all_servers}

    # 2. Generate GOST config
    gost_config_dict = generate_gost_config(transits_to_configure, servers_map)
    gost_config_json = json.dumps(gost_config_dict, indent=4)

    # New path for gost_config.json within the app's instance folder
    config_filename = 'gost_config.json'
    config_path = os.path.join(app.instance_path, config_filename)
    # Use a temporary file within the instance path as well for atomic write attempt
    temp_config_path = os.path.join(app.instance_path, f"{config_filename}.tmp")

    # 3. Write generated JSON to GOST config file in instance_path
    write_success = False
    write_error_msg = ""
    try:
        with open(temp_config_path, 'w') as f:
            f.write(gost_config_json)
        
        # Atomically move the temporary file to the final path within instance folder
        # No sudo needed as this is within the app's writable area.
        os.rename(temp_config_path, config_path)
        write_success = True
        flash(_("Successfully wrote GOST configuration to %(config_path)s.", config_path=config_path), 'success')
        print(f"Info: GOST configuration written to {config_path}")

    except Exception as e:
        write_error_msg = _("Error writing GOST config to %(config_path)s: %(error)s", config_path=config_path, error=str(e))
        flash(write_error_msg, 'error') # Flash the error message directly
        print(f"Error: {write_error_msg}")
        # Attempt to clean up temp file if it exists
        if os.path.exists(temp_config_path):
            try:
                os.remove(temp_config_path)
            except OSError:
                pass # Ignore errors on cleanup

    # 4. Restart GOST service
    # IMPORTANT: Restarting a system-wide GOST service from a web app is problematic on PaaS
    # like PythonAnywhere. The `restart_gost_service()` uses `sudo systemctl`, which won't work
    # without specific sudo privileges for the web app user.
    # This part will likely fail or need adjustment for PythonAnywhere.
    # For now, the logic remains, but it's a deployment consideration.
    # If GOST is run by the same user and configured to use the instance_path config,
    # then a non-sudo restart command might be possible if GOST is managed by supervisord/user systemd.
    restart_msg = ""
    if write_success:
        success, restart_msg = restart_gost_service()
        if success:
            flash(_("GOST service restarted successfully. %(restart_msg)s", restart_msg=restart_msg), 'success')
            # 5. Update transit statuses
            try:
                for t in transits_to_configure:
                    t.status = 'active' # Assuming restart means they are now active
                db.session.commit()
                flash(_("Relevant transit statuses updated to 'active'."), "info")
            except Exception as e:
                db.session.rollback()
                flash(_("Error updating transit statuses: %(error)s", error=str(e)), "error")
        else:
            flash(_("Failed to restart GOST service: %(restart_msg)s. Manual check required.", restart_msg=restart_msg), 'error')
            # Update status to 'error' for pending/active transits if restart fails
            try:
                for t in transits_to_configure:
                    t.status = 'error'
                    t.updated_at = db.func.now() # Ensure updated_at is set
                db.session.commit()
                flash(_("Relevant transit statuses updated to 'error' due to GOST restart failure."), "warning")
            except Exception as e:
                db.session.rollback()
                flash(_("Error updating transit statuses to 'error': %(error)s", error=str(e)), "error")
    else:
        # If writing config failed, don't attempt restart, mark transits as error
        flash(_("GOST service was not restarted due to configuration write failure."), 'warning')
        try:
            for t in transits_to_configure:
                if t.status == 'pending': # Only update pending ones to error, active ones remain error from previous attempts or active
                    t.status = 'error'
                    t.updated_at = db.func.now()
            db.session.commit()
            flash(_("Pending transit statuses updated to 'error' due to config write failure."), "warning")
        except Exception as e:
            db.session.rollback()
            flash(_("Error updating transit statuses to 'error': %(error)s", error=str(e)), "error")

    return redirect(url_for('list_transits'))


@app.route('/status')
def status_page():
    all_servers = models.Servers.query.order_by(models.Servers.name).all()
    # Eager load server_a and server_b relationships to avoid N+1 queries in template
    all_transits = models.Transits.query.options(
        db.joinedload(models.Transits.server_a),
        db.joinedload(models.Transits.server_b)
    ).order_by(models.Transits.name).all()
    
    return render_template('status_display.html', servers=all_servers, transits=all_transits)

@app.route('/list_transits')
def list_transits():
    transits = models.Transits.query.all()
    # You might want to fetch server names for server_a_id and server_b_id for better display
    return render_template('list_transits.html', transits=transits)


if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
