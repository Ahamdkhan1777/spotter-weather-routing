"""Verify an actual running same-origin deployment; no fixture responses or API keys."""
import json
import re
import sys
from urllib.request import urlopen

base = (sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8001').rstrip('/')
with urlopen(base + '/api/health/', timeout=15) as response:
    assert response.status == 200
    health = json.load(response)
    assert health['status'] == 'ok' and health['demo_mode'] is False
with urlopen(base + '/', timeout=15) as response:
    assert response.status == 200
    html = response.read().decode()
    assert 'Spotter AI' in html and '<div id="root">' in html
assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
assert len(assets) >= 2, 'Production JavaScript/CSS asset references missing'
for path in assets:
    with urlopen(base + path, timeout=15) as response:
        assert response.status == 200 and len(response.read()) > 100
print(json.dumps({'same_origin_http_verified': True, 'frontend': 200, 'health': health, 'assets_verified': len(assets)}))
