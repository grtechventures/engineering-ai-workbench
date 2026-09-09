"""Default-deny model egress. OS firewall remains the independent boundary."""
import ipaddress
import os
from urllib.parse import urlsplit


def validate_model_url(url):
    parts=urlsplit(url)
    if parts.scheme not in ('http','https') or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError('Model URL must be HTTP(S), without credentials, query or fragment')
    host=parts.hostname
    if host=='localhost':
        # Avoid name resolution: use a literal loopback destination.
        host='127.0.0.1'
    try: address=ipaddress.ip_address(host or '')
    except ValueError as exc:
        raise ValueError('Use a literal loopback or explicitly approved private LAN IP for the model') from exc
    if not address.is_loopback:
        approved={x.strip() for x in os.getenv('EWB_APPROVED_MODEL_IPS','').split(',') if x.strip()}
        lan=any(address in network for network in (
            ipaddress.ip_network('10.0.0.0/8'),ipaddress.ip_network('172.16.0.0/12'),
            ipaddress.ip_network('192.168.0.0/16'),ipaddress.ip_network('fc00::/7')) if network.version==address.version)
        if not lan or os.getenv('EWB_APPROVED_ONPREM')!='1' or str(address) not in approved:
            raise ValueError('Model network access denied: approve an exact private LAN IP or use loopback')
    authority=('['+str(address)+']') if address.version==6 else str(address)
    if parts.port:authority+=':'+str(parts.port)
    return parts._replace(netloc=authority).geturl().rstrip('/')
