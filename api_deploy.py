import os
import subprocess
import sys
from flask import Blueprint, request, jsonify, current_app

deploy_bp = Blueprint('deploy', __name__)

@deploy_bp.route('/api/deploy_trigger', methods=['POST'])
def trigger_deploy():
    """
    Webhook endpoint to trigger local deployment script.
    Requires 'X-Deploy-Secret' header matching config.
    """
    secret = request.headers.get('X-Deploy-Secret')
    expected_secret = os.environ.get('DEPLOY_SECRET', 'change-this-secret-in-pythonanywhere-env')
    
    if secret != expected_secret:
        return jsonify({"error": "Unauthorized"}), 403

    deploy_script = os.path.join(current_app.root_path, 'deploy.sh')
    
    if not os.path.exists(deploy_script):
        return jsonify({"error": "deploy.sh not found"}), 404

    try:
        # Determine command based on OS
        if sys.platform == 'win32':
            # Windows fallback (Git Bash or similar required, likely won't work natively without shell)
            # Just listing files as mock for local verification
            cmd = ['cmd', '/c', 'echo "Mock Deploy on Windows"']
        else:
            # Linux (PythonAnywhere)
            cmd = ['bash', deploy_script]

        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            cwd=current_app.root_path
        )
        
        if result.returncode == 0:
            return jsonify({
                "status": "success", 
                "output": result.stdout
            }), 200
        else:
            return jsonify({
                "status": "error", 
                "output": result.stdout, 
                "error": result.stderr
            }), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500
