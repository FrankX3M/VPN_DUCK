# Gunicorn configuration file

# Server socket binding
bind = "0.0.0.0:5000"

# Worker processes
workers = 2
worker_class = "sync"
worker_tmp_dir = "/dev/shm"
timeout = 120

# Logging
loglevel = "debug"
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stdout
capture_output = True
disable_redirect_access_to_syslog = True

# Process naming
proc_name = "vpn_duck_admin"

# Improve performance
sendfile = False  # Disable sendfile to avoid the error