import base64
import os
import uuid
import time

def save_signature(base64_data, instance_path, prefix="sig"):
    """
    Decodes base64 PNG data and saves it.
    Returns the relative path from instance/
    """
    if not base64_data:
        raise ValueError("No signature data provided")
        
    sig_dir = os.path.join(instance_path, 'signatures')
    os.makedirs(sig_dir, exist_ok=True)

    if ',' in base64_data:
        _, encoded = base64_data.split(',', 1)
    else:
        encoded = base64_data

    # Generate filename with timestamp
    filename = f"{prefix}_{int(time.time())}_{uuid.uuid4().hex[:8]}.png"
    filepath = os.path.join(sig_dir, filename)

    with open(filepath, "wb") as f:
        f.write(base64.b64decode(encoded))

    return f"signatures/{filename}"
