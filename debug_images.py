
import requests
from bs4 import BeautifulSoup

url = "https://techcrunch.com/2026/01/15/microsoft-taps-indias-varaha-for-asia-first-durable-carbon-removal-offtake/"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.content, "html.parser")
    
    print(f"Title: {soup.title.string}")
    
    # Check potential containers
    containers = [
        ("article", soup.find("article")),
        ("main", soup.find("main")),
        ("div.content", soup.find("div", class_="content")),
        ("div.article-content", soup.find("div", class_="article-content")),
        ("div.entry-content", soup.find("div", class_="entry-content")), # Common WP
    ]
    
    for name, container in containers:
        if container:
            imgs = container.find_all("img")
            print(f"\n--- Container: {name} ---")
            print(f"Found {len(imgs)} images")
            for i, img in enumerate(imgs):
                print(f"[{i}] src: {img.get('src')}")
                print(f"    class: {img.get('class')}")
                print(f"    alt: {img.get('alt')}")
                # Check for lazy loading attributes
                print(f"    data-src: {img.get('data-src')}")
                print(f"    srcset: {img.get('srcset')}")
        else:
            print(f"\n--- Container: {name} NOT FOUND ---")
            
except Exception as e:
    print(e)
