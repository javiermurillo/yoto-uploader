"""mitmproxy addon to capture upload traffic from Yoto.

Usage:
    mitmweb -s debug_tools/mitm_addon.py

It will log all POST/PUT requests to 'mitm_traffic.json' in the current directory.
"""

import json
import os
from mitmproxy import http

# Output file
LOG_FILE = "mitm_traffic.json"

# Clear log on start
if os.path.exists(LOG_FILE):
    os.remove(LOG_FILE)

def request(flow: http.HTTPFlow) -> None:
    """Intercept request headers and body."""
    
    # Filter: We care about POST/PUT (likely uploads/mutations)
    if flow.request.method not in ["POST", "PUT"]:
        return

    # Filter: Reduce noise (analytics, logging, static assets)
    ignored_domains = [
        "google-analytics.com",
        "stats.g.doubleclick.net",
        "log.cookieyes.com",
        "sentry.io",
        "fonts.googleapis.com"
    ]
    if any(d in flow.request.host for d in ignored_domains):
        return

    print(f"[MITM] 📸 Capturing {flow.request.method} {flow.request.url}")

    # Extract body snippet (safe for JSON/binary)
    content = flow.request.content
    try:
        # Try to parse as JSON first
        data = json.loads(content)
        data_type = "json"
    except:
        # If binary/text, take a snippet
        # We assume upload might be multipart or binary
        data = f"<binary/text: {len(content)} bytes>"
        data_type = "binary"

    entry = {
        "method": flow.request.method,
        "url": flow.request.url,
        "headers": dict(flow.request.headers),
        "data_type": data_type,
        "data_preview": str(data)[:500] if data_type == "binary" else data
    }

    # Append to JSON list
    log_data = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                log_data = json.load(f)
        except:
            pass
    
    log_data.append(entry)
    
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=2)
