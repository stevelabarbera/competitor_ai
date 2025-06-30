import os
import asyncio
import trafilatura
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import requests
import re

# === Config ===
OUTPUT_DIR = "output"
KEYWORDS = [r"attack surface management", r"external exposure", r"asset inventory"]

# Regex patterns: key = regex, value = True to allow, False to deny
LINK_FILTERS = {
    r"/(privacy|terms|login)": False,
    r"attack-surface-management": True,
    r"/blog/.*": True,
}

MAX_DEPTH = 2
VISITED = set()

# === Utils ===
def sanitize_filename(url):
    return urlparse(url).netloc.replace(".", "_")

def is_internal(base_url, target_url):
    return urlparse(base_url).netloc == urlparse(target_url).netloc

def matches_keywords(text):
    for pattern in KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def should_follow_url(url, filters):
    for pattern, allow in filters.items():
        if re.search(pattern, url):
            print(f"[Filter] URL matched '{pattern}' → {'ALLOW' if allow else 'DENY'}")
            return allow
    print(f"[Filter] URL matched no pattern → ALLOW")
    return True

def save_text(url, text):
    domain = sanitize_filename(url)
    path = os.path.join(OUTPUT_DIR, domain)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "content.txt"), "a", encoding="utf-8") as f:
        f.write(f"\n\n=== {url} ===\n{text}")

def download_pdf(pdf_url, save_dir):
    try:
        response = requests.get(pdf_url)
        if response.status_code == 200:
            filename = os.path.join(save_dir, os.path.basename(pdf_url))
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"[PDF] Downloaded: {pdf_url}")
    except Exception as e:
        print(f"[PDF] Failed to download {pdf_url}: {e}")

# === Main Crawl Logic ===
async def crawl_page(playwright, url, base_url, depth):
    if depth > MAX_DEPTH or url in VISITED:
        return
    VISITED.add(url)

    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()

    try:
        print(f"[Crawl] Visiting: {url} (depth {depth})")
        await page.goto(url, timeout=60000)
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # === Extract PDFs ===
        domain = sanitize_filename(base_url)
        pdf_dir = os.path.join(OUTPUT_DIR, domain, "pdfs")
        os.makedirs(pdf_dir, exist_ok=True)

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                full_url = urljoin(url, href)
                download_pdf(full_url, pdf_dir)

        # === Extract if relevant ===
        if matches_keywords(url) or matches_keywords(soup.get_text()):
            extracted = trafilatura.extract(html)
            if extracted:
                print(f"[Extract] ✅ Relevant content from: {url}")
                save_text(url, extracted)
            else:
                print(f"[Extract] ❌ Could not extract from: {url}")
        else:
            print(f"[Extract] 🔕 Irrelevant: {url}")

        # === Crawl internal links ===
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(url, href)
            if is_internal(base_url, full_url) and full_url not in VISITED:
                if should_follow_url(full_url, LINK_FILTERS):
                    await crawl_page(playwright, full_url, base_url, depth + 1)

    except Exception as e:
        print(f"[Error] {url}: {e}")
    finally:
        await browser.close()

# === Entrypoint ===
async def main(start_urls):
    async with async_playwright() as playwright:
        for url in start_urls:
            await crawl_page(playwright, url, url, depth=0)

if __name__ == "__main__":
    competitor_urls = [f"https://tenable.com"]#[f"https://censys.com","https://shodan.io","https://www.paloaltonetworks.com","https://www.cycognito.com"]
    asyncio.run(main(competitor_urls))