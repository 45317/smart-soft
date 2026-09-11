"""
SmartSoft Launcher
Starts PostgreSQL, Django server, opens browser, and shows system tray icon.
"""
import os
import sys
import time
import json
import subprocess
import threading
import webbrowser
import signal
import ctypes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.ini")


def load_config():
    config = {
        "host": "0.0.0.0",
        "port": "8000",
        "db_name": "soft_smart",
        "db_user": "postgres",
        "db_password": "",
        "db_port": "5432",
        "api_key": "dev-key-change-me",
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        config[key.strip()] = value.strip()
        except Exception:
            pass
    return config


def save_config(config):
    lines = [
        "# SmartSoft Configuration",
        "# Change these values as needed",
        "",
        f"host = {config.get('host', '0.0.0.0')}",
        f"port = {config.get('port', '8000')}",
        f"db_name = {config.get('db_name', 'soft_smart')}",
        f"db_user = {config.get('db_user', 'postgres')}",
        f"db_password = {config.get('db_password', '')}",
        f"db_port = {config.get('db_port', '5432')}",
        f"api_key = {config.get('api_key', 'dev-key-change-me')}",
    ]
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def find_postgresql():
    """Find PostgreSQL binaries in the bundled directory."""
    pg_dir = os.path.join(BASE_DIR, "postgresql")
    if not os.path.exists(pg_dir):
        return None
    bin_dir = os.path.join(pg_dir, "bin")
    if not os.path.exists(bin_dir):
        return None
    initdb = os.path.join(bin_dir, "initdb.exe")
    pg_ctl = os.path.join(bin_dir, "pg_ctl.exe")
    postgres = os.path.join(bin_dir, "postgres.exe")
    if os.path.exists(pg_ctl) and os.path.exists(postgres):
        return {"bin": bin_dir, "initdb": initdb, "pg_ctl": pg_ctl, "postgres": postgres}
    return None


def init_database(pg):
    """Initialize PostgreSQL database cluster."""
    data_dir = os.path.join(BASE_DIR, "postgresql", "data")
    if os.path.exists(data_dir) and os.listdir(data_dir):
        return True
    os.makedirs(data_dir, exist_ok=True)
    config = load_config()
    try:
        subprocess.run(
            [pg["initdb"], "-D", data_dir, "-U", config["db_user"], "--encoding=UTF8", "--locale=C"],
            capture_output=True, timeout=60
        )
        return True
    except Exception as e:
        print(f"Database init error: {e}")
        return False


def start_postgresql(pg):
    """Start PostgreSQL server."""
    config = load_config()
    data_dir = os.path.join(BASE_DIR, "postgresql", "data")
    log_file = os.path.join(BASE_DIR, "postgresql", "postgresql.log")

    subprocess.run(
        [pg["pg_ctl"], "-D", data_dir, "-l", log_file, "start", "-w",
         "-o", f"-p {config['db_port']} -c listen_addresses=*"],
        capture_output=True, timeout=30
    )
    return True


def stop_postgresql(pg):
    """Stop PostgreSQL server."""
    data_dir = os.path.join(BASE_DIR, "postgresql", "data")
    subprocess.run(
        [pg["pg_ctl"], "-D", data_dir, "stop", "-m", "fast"],
        capture_output=True, timeout=10
    )


def create_database(pg):
    """Create the database if it doesn't exist."""
    config = load_config()
    createdb = os.path.join(pg["bin"], "createdb.exe")
    psql = os.path.join(pg["bin"], "psql.exe")

    try:
        subprocess.run(
            [createdb, "-U", config["db_user"], "-p", config["db_port"], config["db_name"]],
            capture_output=True, timeout=10
        )
    except Exception:
        pass


def run_migrations():
    """Run Django migrations."""
    sys.path.insert(0, BASE_DIR)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

    try:
        import django
        django.setup()
        from django.core.management import call_command
        call_command("migrate", verbosity=0)
        return True
    except Exception as e:
        print(f"Migration error: {e}")
        return False


def create_superuser():
    """Create default admin user if none exists."""
    try:
        import django
        from django.contrib.auth.models import User
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser("admin", "admin@smartsoft.com", "admin123")
            print("Default admin created: admin / admin123")
    except Exception:
        pass


def start_django(config):
    """Start Django server in background."""
    sys.path.insert(0, BASE_DIR)
    os.environ["DJANGO_SETTINGS_MODULE"] = "project.settings"
    os.environ["RAG_API_KEY"] = config.get("api_key", "dev-key-change-me")

    import django
    django.setup()
    from django.core.management import call_command
    from django.contrib.staticfiles.management.commands.runserver import Command as RunServerCommand

    host = config.get("host", "0.0.0.0")
    port = config.get("port", "8000")

    def run():
        call_command("runserver", f"{host}:{port}", "--noreload", verbosity=0)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


def open_browser(config):
    """Open browser to the app."""
    port = config.get("port", "8000")
    url = f"http://localhost:{port}"
    time.sleep(3)
    webbrowser.open(url)


def show_tray_icon(on_quit):
    """Show system tray icon."""
    try:
        import pystray
        from PIL import Image, ImageDraw

        def create_image():
            img = Image.new("RGB", (64, 64), "#2196F3")
            dc = ImageDraw.Draw(img)
            dc.rectangle([16, 16, 48, 48], fill="white")
            dc.text((22, 20), "SS", fill="#2196F3")
            return img

        menu = pystray.Menu(
            pystray.MenuItem("Open", lambda: webbrowser.open(f"http://localhost:{config.get('port', '8000')}")),
            pystray.MenuItem("Quit", on_quit),
        )
        icon = pystray.Icon("SmartSoft", create_image(), "SmartSoft", menu)
        return icon
    except ImportError:
        return None


def main():
    print("=" * 50)
    print("  SmartSoft - Starting...")
    print("=" * 50)

    config = load_config()
    save_config(config)

    pg = find_postgresql()
    if pg:
        print("PostgreSQL found")
        if not init_database(pg):
            print("Failed to initialize database")
            return
        start_postgresql(pg)
        create_database(pg)
        print("PostgreSQL started")
    else:
        print("PostgreSQL not found - using external PostgreSQL")
        print(f"Make sure PostgreSQL is running on port {config.get('db_port', '5432')}")

    print("Running migrations...")
    if not run_migrations():
        print("Failed to run migrations")
        return

    create_superuser()

    print("Loading AI models (first run downloads ~1.5GB)...")
    print("Starting Django server...")
    start_django(config)

    print("Opening browser...")
    threading.Thread(target=open_browser, args=(config,), daemon=True).start()

    quit_event = threading.Event()

    def on_quit(icon, item):
        quit_event.set()
        icon.stop()

    icon = show_tray_icon(on_quit)
    if icon:
        print("System tray icon active - right-click to quit")
        tray_thread = threading.Thread(target=icon.run, daemon=True)
        tray_thread.start()

    print(f"SmartSoft running at http://localhost:{config.get('port', '8000')}")
    print("Press Ctrl+C to stop")

    try:
        quit_event.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        if pg:
            stop_postgresql(pg)
        print("Goodbye!")


if __name__ == "__main__":
    main()
