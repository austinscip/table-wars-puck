"""
Flask Routes for OTA Firmware Updates
Manages firmware versions, downloads, and update tracking
"""

from flask import Blueprint, request, jsonify, send_file
from datetime import datetime
import os
import hashlib
import json

firmware_bp = Blueprint('firmware', __name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

FIRMWARE_DIR = os.path.join(os.path.dirname(__file__), 'firmware_versions')
FIRMWARE_MANIFEST = os.path.join(FIRMWARE_DIR, 'manifest.json')

# Ensure firmware directory exists
os.makedirs(FIRMWARE_DIR, exist_ok=True)

# ============================================================================
# FIRMWARE VERSION MANAGEMENT
# ============================================================================

def load_manifest():
    """Load firmware manifest (version history)"""
    if os.path.exists(FIRMWARE_MANIFEST):
        with open(FIRMWARE_MANIFEST, 'r') as f:
            return json.load(f)
    return {
        "versions": [],
        "latest": "1.0.0",
        "min_supported": "1.0.0"
    }

def save_manifest(manifest):
    """Save firmware manifest"""
    with open(FIRMWARE_MANIFEST, 'w') as f:
        json.dump(manifest, f, indent=2)

def get_latest_version():
    """Get the latest firmware version"""
    manifest = load_manifest()
    return manifest.get("latest", "1.0.0")

def get_firmware_path(version):
    """Get file path for a specific firmware version"""
    return os.path.join(FIRMWARE_DIR, f"firmware_{version}.bin")

def calculate_md5(file_path):
    """Calculate MD5 checksum of firmware file"""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

# ============================================================================
# PUCK UPDATE TRACKING
# ============================================================================

# Track which pucks have which firmware versions
puck_versions = {}  # {puck_id: {"version": "1.2.0", "last_update": timestamp, "last_seen": timestamp}}

def update_puck_version(puck_id, version):
    """Record a puck's firmware version"""
    puck_versions[puck_id] = {
        "version": version,
        "last_update": datetime.now().isoformat(),
        "last_seen": datetime.now().isoformat()
    }

def get_puck_version(puck_id):
    """Get a puck's current firmware version"""
    if puck_id in puck_versions:
        puck_versions[puck_id]["last_seen"] = datetime.now().isoformat()
        return puck_versions[puck_id].get("version", "1.0.0")
    return "1.0.0"  # Default version for unknown pucks

# ============================================================================
# REST API ROUTES
# ============================================================================

@firmware_bp.route('/firmware/version', methods=['GET'])
def check_version():
    """
    Check if firmware update is available
    GET /firmware/version?puck_id=1

    Returns: {"version": "1.2.0", "url": "/firmware/download/1.2.0", "md5": "abc123..."}
    """
    puck_id = request.args.get('puck_id', type=int)

    if not puck_id:
        return jsonify({"error": "puck_id required"}), 400

    latest_version = get_latest_version()
    current_version = get_puck_version(puck_id)

    firmware_path = get_firmware_path(latest_version)

    if not os.path.exists(firmware_path):
        return jsonify({
            "error": "Firmware file not found",
            "version": latest_version
        }), 404

    md5_checksum = calculate_md5(firmware_path)
    file_size = os.path.getsize(firmware_path)

    response = {
        "version": latest_version,
        "current_version": current_version,
        "update_available": latest_version != current_version,
        "url": f"/firmware/download/{latest_version}",
        "md5": md5_checksum,
        "size": file_size,
        "release_date": datetime.now().isoformat()
    }

    return jsonify(response)


@firmware_bp.route('/firmware/download/<version>', methods=['GET'])
def download_firmware(version):
    """
    Download a specific firmware version
    GET /firmware/download/1.2.0?puck_id=1

    Returns: Binary firmware file (.bin)
    """
    puck_id = request.args.get('puck_id', type=int)

    firmware_path = get_firmware_path(version)

    if not os.path.exists(firmware_path):
        return jsonify({"error": f"Firmware version {version} not found"}), 404

    print(f"📥 Puck {puck_id} downloading firmware {version}")

    return send_file(
        firmware_path,
        as_attachment=True,
        download_name=f"firmware_{version}.bin",
        mimetype='application/octet-stream'
    )


@firmware_bp.route('/firmware/report-success', methods=['POST'])
def report_update_success():
    """
    Puck reports successful firmware update
    POST /firmware/report-success
    Body: {"puck_id": 1, "version": "1.2.0", "previous_version": "1.1.0"}
    """
    data = request.get_json()
    puck_id = data.get('puck_id')
    version = data.get('version')
    previous_version = data.get('previous_version')

    if not puck_id or not version:
        return jsonify({"error": "puck_id and version required"}), 400

    update_puck_version(puck_id, version)

    print(f"✅ Puck {puck_id} successfully updated:")
    print(f"   {previous_version} → {version}")

    return jsonify({
        "success": True,
        "message": "Update success recorded",
        "puck_id": puck_id,
        "version": version
    })


@firmware_bp.route('/firmware/report-failure', methods=['POST'])
def report_update_failure():
    """
    Puck reports failed firmware update
    POST /firmware/report-failure
    Body: {"puck_id": 1, "version": "1.2.0", "error": "MD5 mismatch"}
    """
    data = request.get_json()
    puck_id = data.get('puck_id')
    version = data.get('version')
    error = data.get('error', 'Unknown error')

    if not puck_id or not version:
        return jsonify({"error": "puck_id and version required"}), 400

    print(f"❌ Puck {puck_id} update failed:")
    print(f"   Version: {version}")
    print(f"   Error: {error}")

    # Log failure for diagnostics
    failure_log = os.path.join(FIRMWARE_DIR, 'update_failures.log')
    with open(failure_log, 'a') as f:
        f.write(f"{datetime.now().isoformat()} | Puck {puck_id} | {version} | {error}\n")

    return jsonify({
        "success": True,
        "message": "Failure recorded"
    })


@firmware_bp.route('/firmware/fleet-status', methods=['GET'])
def get_fleet_status():
    """
    Get firmware status of entire puck fleet
    GET /firmware/fleet-status

    Returns: List of all pucks and their firmware versions
    """
    fleet_status = []
    latest_version = get_latest_version()

    for puck_id, info in puck_versions.items():
        fleet_status.append({
            "puck_id": puck_id,
            "version": info["version"],
            "up_to_date": info["version"] == latest_version,
            "last_update": info["last_update"],
            "last_seen": info["last_seen"]
        })

    # Sort by puck_id
    fleet_status.sort(key=lambda x: x['puck_id'])

    return jsonify({
        "latest_version": latest_version,
        "total_pucks": len(fleet_status),
        "up_to_date": sum(1 for p in fleet_status if p["up_to_date"]),
        "outdated": sum(1 for p in fleet_status if not p["up_to_date"]),
        "pucks": fleet_status
    })


@firmware_bp.route('/firmware/upload', methods=['POST'])
def upload_firmware():
    """
    Upload a new firmware version (admin only)
    POST /firmware/upload
    Form data:
      - file: firmware binary (.bin)
      - version: version string (e.g., "1.2.0")
      - release_notes: optional release notes
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    version = request.form.get('version')
    release_notes = request.form.get('release_notes', '')

    if not version:
        return jsonify({"error": "Version required"}), 400

    if not file.filename.endswith('.bin'):
        return jsonify({"error": "File must be .bin format"}), 400

    # Save firmware file
    firmware_path = get_firmware_path(version)
    file.save(firmware_path)

    # Calculate MD5
    md5_checksum = calculate_md5(firmware_path)
    file_size = os.path.getsize(firmware_path)

    # Update manifest
    manifest = load_manifest()

    version_info = {
        "version": version,
        "upload_date": datetime.now().isoformat(),
        "md5": md5_checksum,
        "size": file_size,
        "release_notes": release_notes
    }

    # Add to versions list
    manifest["versions"].append(version_info)

    # Update latest version
    manifest["latest"] = version

    save_manifest(manifest)

    print(f"✅ New firmware uploaded: {version}")
    print(f"   Size: {file_size} bytes")
    print(f"   MD5: {md5_checksum}")

    return jsonify({
        "success": True,
        "message": "Firmware uploaded successfully",
        "version": version,
        "md5": md5_checksum,
        "size": file_size
    })


@firmware_bp.route('/firmware/versions', methods=['GET'])
def list_versions():
    """
    List all available firmware versions
    GET /firmware/versions
    """
    manifest = load_manifest()

    return jsonify({
        "latest": manifest.get("latest"),
        "min_supported": manifest.get("min_supported"),
        "versions": manifest.get("versions", [])
    })


@firmware_bp.route('/firmware/set-latest', methods=['POST'])
def set_latest_version():
    """
    Set which version is the latest (rollback capability)
    POST /firmware/set-latest
    Body: {"version": "1.1.0"}
    """
    data = request.get_json()
    version = data.get('version')

    if not version:
        return jsonify({"error": "Version required"}), 400

    firmware_path = get_firmware_path(version)

    if not os.path.exists(firmware_path):
        return jsonify({"error": f"Firmware version {version} not found"}), 404

    manifest = load_manifest()
    manifest["latest"] = version
    save_manifest(manifest)

    print(f"✅ Latest firmware version set to: {version}")

    return jsonify({
        "success": True,
        "message": f"Latest version set to {version}",
        "version": version
    })


# ============================================================================
# ADMIN DASHBOARD ROUTE
# ============================================================================

@firmware_bp.route('/firmware/dashboard')
def firmware_dashboard():
    """HTML dashboard for firmware management"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Firmware Management Dashboard</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: #1a1a1a;
                color: #ffffff;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            h1 {
                color: #00ff88;
                border-bottom: 3px solid #00ff88;
                padding-bottom: 10px;
            }
            .card {
                background: #2a2a2a;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            }
            .stat {
                display: inline-block;
                margin: 10px 20px 10px 0;
                font-size: 18px;
            }
            .stat-value {
                color: #00ff88;
                font-size: 32px;
                font-weight: bold;
            }
            .puck-list {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }
            .puck-card {
                background: #333;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #00ff88;
            }
            .puck-card.outdated {
                border-left-color: #ff6b6b;
            }
            .upload-form {
                background: #2a2a2a;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }
            input, textarea, button {
                margin: 10px 0;
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #444;
                background: #333;
                color: #fff;
                font-size: 14px;
            }
            button {
                background: #00ff88;
                color: #000;
                cursor: pointer;
                font-weight: bold;
                border: none;
            }
            button:hover {
                background: #00cc6a;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔧 Firmware Management Dashboard</h1>

            <div class="card">
                <h2>Fleet Status</h2>
                <div id="fleet-stats"></div>
                <div id="puck-list" class="puck-list"></div>
            </div>

            <div class="card">
                <h2>Upload New Firmware</h2>
                <form id="upload-form" enctype="multipart/form-data">
                    <input type="text" id="version" placeholder="Version (e.g., 1.2.0)" required><br>
                    <input type="file" id="firmware-file" accept=".bin" required><br>
                    <textarea id="release-notes" placeholder="Release notes (optional)" rows="4" style="width: 100%;"></textarea><br>
                    <button type="submit">Upload Firmware</button>
                </form>
                <div id="upload-status"></div>
            </div>

            <div class="card">
                <h2>Available Versions</h2>
                <div id="version-list"></div>
            </div>
        </div>

        <script>
            async function loadFleetStatus() {
                const response = await fetch('/firmware/fleet-status');
                const data = await response.json();

                document.getElementById('fleet-stats').innerHTML = `
                    <div class="stat">
                        <div class="stat-value">${data.total_pucks}</div>
                        <div>Total Pucks</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${data.up_to_date}</div>
                        <div>Up to Date</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" style="color: #ff6b6b;">${data.outdated}</div>
                        <div>Outdated</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${data.latest_version}</div>
                        <div>Latest Version</div>
                    </div>
                `;

                document.getElementById('puck-list').innerHTML = data.pucks.map(puck => `
                    <div class="puck-card ${puck.up_to_date ? '' : 'outdated'}">
                        <strong>Puck ${puck.puck_id}</strong><br>
                        Version: ${puck.version} ${puck.up_to_date ? '✅' : '⚠️'}<br>
                        Last seen: ${new Date(puck.last_seen).toLocaleString()}
                    </div>
                `).join('');
            }

            async function loadVersions() {
                const response = await fetch('/firmware/versions');
                const data = await response.json();

                document.getElementById('version-list').innerHTML = `
                    <p><strong>Latest:</strong> ${data.latest}</p>
                    <ul>
                        ${data.versions.map(v => `
                            <li>${v.version} - ${new Date(v.upload_date).toLocaleDateString()} (${(v.size / 1024).toFixed(2)} KB)</li>
                        `).join('')}
                    </ul>
                `;
            }

            document.getElementById('upload-form').addEventListener('submit', async (e) => {
                e.preventDefault();

                const formData = new FormData();
                formData.append('file', document.getElementById('firmware-file').files[0]);
                formData.append('version', document.getElementById('version').value);
                formData.append('release_notes', document.getElementById('release-notes').value);

                const response = await fetch('/firmware/upload', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (result.success) {
                    document.getElementById('upload-status').innerHTML = `
                        <p style="color: #00ff88;">✅ ${result.message}</p>
                    `;
                    loadVersions();
                    loadFleetStatus();
                } else {
                    document.getElementById('upload-status').innerHTML = `
                        <p style="color: #ff6b6b;">❌ ${result.error}</p>
                    `;
                }
            });

            // Load data on page load
            loadFleetStatus();
            loadVersions();

            // Refresh every 10 seconds
            setInterval(loadFleetStatus, 10000);
        </script>
    </body>
    </html>
    """


def init_firmware_routes(app):
    """Initialize firmware update routes"""
    app.register_blueprint(firmware_bp)
    print("✅ Firmware update routes registered")
    print(f"   Firmware directory: {FIRMWARE_DIR}")
    print(f"   Dashboard: http://localhost:5000/firmware/dashboard")
