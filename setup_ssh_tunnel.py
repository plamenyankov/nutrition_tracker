#!/usr/bin/env python3
"""
Setup SSH tunnel for secure MySQL connection
"""

import os
import sys
import subprocess
import time
import signal
import socket
from contextlib import closing

def check_port_available(port):
    """Check if a port is available on localhost"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        return sock.connect_ex(('localhost', port)) != 0

def find_available_port(start_port=3307):
    """Find an available port starting from start_port"""
    port = start_port
    while not check_port_available(port):
        port += 1
        if port > start_port + 100:  # Avoid infinite loop
            raise Exception("No available ports found")
    return port

def setup_ssh_tunnel():
    """Setup SSH tunnel for MySQL connection"""

    print("="*60)
    print("SSH Tunnel Setup for MySQL")
    print("="*60)

    # Get SSH connection details
    ssh_host = input("SSH Host (server with MySQL access): ").strip()
    if not ssh_host:
        print("SSH host is required")
        return False

    ssh_user = input(f"SSH Username [{os.getenv('USER', 'root')}]: ").strip() or os.getenv('USER', 'root')
    ssh_port = input("SSH Port [22]: ").strip() or "22"

    # MySQL connection details
    mysql_host = input("MySQL Host (as seen from SSH server) [192.168.11.1]: ").strip() or "192.168.11.1"
    mysql_port = input("MySQL Port [3306]: ").strip() or "3306"

    # Local tunnel port
    local_port = find_available_port(3307)
    print(f"Using local port: {local_port}")

    # Build SSH tunnel command
    ssh_command = [
        "ssh",
        "-N",  # Don't execute remote command
        "-L", f"{local_port}:{mysql_host}:{mysql_port}",  # Local port forwarding
        "-p", ssh_port,
        f"{ssh_user}@{ssh_host}"
    ]

    print(f"\nSSH Tunnel Command:")
    print(" ".join(ssh_command))

    print(f"\nStarting SSH tunnel...")
    print(f"Local port {local_port} -> {ssh_host} -> {mysql_host}:{mysql_port}")

    try:
        # Start SSH tunnel
        process = subprocess.Popen(ssh_command)

        # Wait a moment for tunnel to establish
        time.sleep(3)

        # Check if tunnel is working
        if process.poll() is None:
            print("✓ SSH tunnel established successfully")

            # Create environment file for tunnel
            env_content = f"""# SSH Tunnel Configuration
USE_SSH_TUNNEL=true
SSH_TUNNEL_LOCAL_HOST=localhost
SSH_TUNNEL_LOCAL_PORT={local_port}

# Original MySQL server details (for reference)
DB_HOST={mysql_host}
DB_PORT={mysql_port}
DB_USER=remote_user
DB_PASS=BuGr@d@N4@loB6!

# Database names
DB_NAME_DEV=nutri_tracker_dev
DB_NAME_PROD=nutri_tracker_prod

# Application settings
FLASK_ENV=development
USE_MYSQL=true
SECRET_KEY=dev-secret-key-change-in-production
"""

            with open('.env.tunnel', 'w') as f:
                f.write(env_content)

            print(f"✓ Environment file created: .env.tunnel")

            print(f"\nTo use the tunnel:")
            print(f"1. Keep this terminal open (tunnel is running)")
            print(f"2. In another terminal, run:")
            print(f"   export $(cat .env.tunnel | xargs)")
            print(f"   python test_mysql_connection.py")
            print(f"3. Or load the environment file in your application")

            print(f"\nPress Ctrl+C to stop the tunnel")

            # Keep tunnel running
            try:
                process.wait()
            except KeyboardInterrupt:
                print(f"\nStopping SSH tunnel...")
                process.terminate()
                process.wait()
                print("✓ SSH tunnel stopped")

        else:
            print("✗ Failed to establish SSH tunnel")
            return False

    except KeyboardInterrupt:
        print(f"\nTunnel setup cancelled")
        return False
    except Exception as e:
        print(f"✗ Error setting up tunnel: {e}")
        return False

    return True

def show_manual_tunnel_setup():
    """Show manual SSH tunnel setup instructions"""
    print("\n" + "="*60)
    print("MANUAL SSH TUNNEL SETUP")
    print("="*60)

    instructions = """
To manually set up an SSH tunnel:

1. Open a terminal and run:
   ssh -N -L 3307:192.168.11.1:3306 username@ssh-server

   Replace:
   - 3307: Local port (can be any available port)
   - 192.168.11.1:3306: MySQL server as seen from SSH server
   - username@ssh-server: Your SSH connection details

2. Keep that terminal open (tunnel running)

3. In another terminal, set environment variables:
   export USE_SSH_TUNNEL=true
   export SSH_TUNNEL_LOCAL_HOST=localhost
   export SSH_TUNNEL_LOCAL_PORT=3307
   export DB_USER=remote_user
   export DB_PASS=BuGr@d@N4@loB6!
   export DB_NAME_DEV=nutri_tracker_dev
   export USE_MYSQL=true

4. Test the connection:
   python test_mysql_connection.py

5. Run migration:
   python migrate_to_mysql.py
"""

    print(instructions)

if __name__ == "__main__":
    print("Choose setup method:")
    print("1. Automated SSH tunnel setup")
    print("2. Show manual setup instructions")

    choice = input("\nEnter choice (1 or 2): ").strip()

    if choice == "2":
        show_manual_tunnel_setup()
    else:
        success = setup_ssh_tunnel()
        if not success:
            print("\nIf automated setup failed, you can use manual setup:")
            show_manual_tunnel_setup()

        sys.exit(0 if success else 1)
