# domain_utils.py
import tldextract
#from tld import get_tld

def extract_root_domain(value: str) -> str:
    """
    Extracts the root domain (e.g., 'example.com') from a URL, hostname, or full domain.
    Handles edge cases like 'sub.example.co.uk' → 'example.co.uk'.
    """
    if not value:
        return "unknown"

    try:
        #res = get_tld("http://some.subdomain.google.co.uk", as_object=True)
        #res.domain
        #'google'
        #res.fld
        # 'google.co.uk'
        ext = tldextract.extract(value)
        if ext.domain and ext.suffix:
            return f"{ext.domain}.{ext.suffix}".lower()
        elif ext.domain:
            return ext.domain.lower()
    except Exception:
        pass

    return value.lower()
