import os
import requests
import toml
from pathlib import Path

PAPER_API = "https://api.papermc.io/v2/projects/velocity"
MODRINTH_API = "https://api.modrinth.com/v2"

def get_latest_velocity():
    response = requests.get(PAPER_API)
    response.raise_for_status()
    latest_version = response.json()["versions"][-1]
    
    response = requests.get(f"{PAPER_API}/versions/{latest_version}")
    response.raise_for_status()
    latest_build = response.json()["builds"][-1]
    
    response = requests.get(f"{PAPER_API}/versions/{latest_version}/builds/{latest_build}")
    response.raise_for_status()
    download_name = response.json()["downloads"]["application"]["name"]
    
    download_url = f"{PAPER_API}/versions/{latest_version}/builds/{latest_build}/downloads/{download_name}"
    return download_url, download_name

def download_file(url, dest):
    print(f"Downloading {url} to {dest}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print("Download complete.")

import secrets
import string

def generate_secret(length=12):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

def setup_velocity_config(install_dir):
    config_path = Path(install_dir) / "velocity.toml"
    
    # Default basic config if it doesn't exist
    default_config = {
        "config-version": "1.0",
        "bind": "0.0.0.0:25577",
        "motd": "#1Velocity Proxy For SecretProject",
        "show-max-players": 500,
        "player-info-forwarding-mode": "none",
        "forwarding-secret": generate_secret(),
        "announce-forge": False,
        "kick-on-proxy-restart": True,
        "online-mode": False,
        "servers": {
            "lobby": "185.9.145.186:25640"
        },
        "forced-hosts": {
            "mc.example.com": ["lobby"]
        },
        "advanced": {
            "compression-threshold": 256,
            "compression-level": -1,
            "login-ratelimit": 3000,
            "connection-timeout": 5000,
            "read-timeout": 30000,
        }
    }
    print("If you see Custom SecretProject IP this for bypass the secretproject ddos protection for joining, you can change it to your own server IP if you want.")
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = toml.load(f)
        except Exception:
            config = default_config
    else:
        config = default_config

    print("\n--- Velocity Configuration ---")
    bind = input(f"Bind address [{config.get('bind', '0.0.0.0:25577')}]: ") or config.get('bind', '0.0.0.0:25577')
    motd = input(f"MOTD [{config.get('motd', '#1Velocity Proxy')}]: ") or config.get('motd', '#1Velocity Proxy')
    forwarding = input(f"Forwarding mode (none, legacy, bungeeguard, modern) [{config.get('player-info-forwarding-mode', 'modern')}]: ") or config.get('player-info-forwarding-mode', 'modern')
    
    config['bind'] = bind
    config['motd'] = motd
    config['player-info-forwarding-mode'] = forwarding
    
    if config.get('forwarding-secret') == "change-me-now" or not config.get('forwarding-secret'):
        config['forwarding-secret'] = generate_secret()
        print(f"Generated new forwarding secret: {config['forwarding-secret']}")

    # Server setup
    print("\n--- Server Setup ---")
    print("Current servers:", config.get('servers', {}))
    add_server = input("Would you like to add/update a server? (y/n) [n]: ").lower() == 'y'
    if add_server:
        s_name = input("Server name (e.g. lobby): ")
        s_address = input("Server address (e.g. 127.0.0.1:25565): ")
        if 'servers' not in config:
            config['servers'] = {}
        config['servers'][s_name] = s_address

    with open(config_path, "w") as f:
        toml.dump(config, f)
    print(f"Configuration saved to {config_path}")

def search_modrinth_plugins(query):
    params = {
        "query": query,
        "facets": '[["categories:velocity"]]'
    }
    response = requests.get(f"{MODRINTH_API}/search", params=params)
    response.raise_for_status()
    return response.json()["hits"]

def download_modrinth_plugin(project_id, plugins_dir):
    # Get latest version for Velocity
    response = requests.get(f"{MODRINTH_API}/project/{project_id}/version")
    response.raise_for_status()
    versions = response.json()
    
    # Filter for velocity loaders (though search already did that, let's be sure)
    velocity_versions = [v for v in versions if "velocity" in v["loaders"]]
    if not velocity_versions:
        print(f"No Velocity version found for project {project_id}")
        return

    latest_version = velocity_versions[0]
    file_info = latest_version["files"][0]
    download_url = file_info["url"]
    filename = file_info["filename"]
    
    download_file(download_url, Path(plugins_dir) / filename)

def main():
    print("--- Velocity Proxy Installer ---")
    
    install_dir = input("Enter installation directory [./velocity]: ") or "./velocity"
    install_path = Path(install_dir).resolve()
    install_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Installing to: {install_path}")
    
    # 1. Download Velocity
    url, name = get_latest_velocity()
    download_file(url, install_path / name)
    
    # 2. Setup Config
    setup_velocity_config(install_path)
    
    # 3. Install Plugins
    plugins_dir = install_path / "plugins"
    plugins_dir.mkdir(exist_ok=True)
    
    # Auto-install ViaVersion
    print("\nAuto-installing ViaVersion...")
    download_modrinth_plugin("P1OZGk5p", plugins_dir)
    
    while True:
        plugin_query = input("\nEnter plugin name to search on Modrinth (or press Enter to skip): ")
        if not plugin_query:
            break
            
        results = search_modrinth_plugins(plugin_query)
        if not results:
            print("No plugins found.")
            continue
            
        print("\nSearch Results:")
        for i, res in enumerate(results[:5]):
            print(f"{i+1}. {res['title']} ({res['project_id']}) - {res['description']}")
            
        choice = input("\nEnter number to install (or 'c' to cancel): ")
        if choice.isdigit() and 1 <= int(choice) <= len(results):
            project_id = results[int(choice)-1]['project_id']
            download_modrinth_plugin(project_id, plugins_dir)
        elif choice.lower() == 'c':
            continue
            
    # 4. Create Start Script
    start_script = install_path / "start.bat"
    with open(start_script, "w") as f:
        f.write(f"@echo off\njava -Xms1G -Xmx1G -jar {name}\npause")
    
    print("\nInstallation complete!")
    print(f"To start Velocity, run: {start_script}")

if __name__ == "__main__":
    main()
