import socket
import ssl
import csv
from datetime import datetime
import whois

# Seed domain list
seed_domains = [
    "pantryshop.com", "snacks.com", "ajcornmeal.com", "auntjemima.com", "capncrunch.com",
    "fritos.com", "tropicana.com", "quakeroats.com", "gatorade.com", "doritos.com"
]

# Get IP address
def resolve_domain(domain):
    try:
        return socket.gethostbyname(domain)
    except:
        return None

# Reverse DNS lookup
def reverse_dns(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except:
        return None

# TLS certificate info
def get_ssl_cert(domain):
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=3) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                san = [entry[1] for entry in cert.get('subjectAltName', [])]
                issuer = ", ".join("=".join(x) for x in cert.get("issuer", [])[0])
                return {
                    "notAfter": cert.get("notAfter"),
                    "subjectAltName": ", ".join(san),
                    "issuer": issuer
                }
    except:
        return {"notAfter": None, "subjectAltName": None, "issuer": None}

# WHOIS org field
def get_whois_org(domain):
    try:
        w = whois.whois(domain)
        return w.org if hasattr(w, "org") else None
    except:
        return None

# Collect enriched results
rows = []
for domain in seed_domains:
    print(f"Processing: {domain}")
    ip = resolve_domain(domain)
    rdns = reverse_dns(ip) if ip else None
    cert_info = get_ssl_cert(domain)
    whois_org = get_whois_org(domain)

    rows.append({
        "Domain": domain,
        "Resolved IP": ip,
        "Reverse DNS": rdns,
        "Cert Expiry": cert_info["notAfter"],
        "Cert SANs": cert_info["subjectAltName"],
        "Cert Issuer": cert_info["issuer"],
        "WHOIS Org": whois_org
    })

# Write to CSV
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
output_file = f"domain_enrichment_{timestamp}.csv"
with open(output_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"\n✔️ Enrichment complete. Results saved to: {output_file}")

