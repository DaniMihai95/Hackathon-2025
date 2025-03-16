import requests
from bs4 import BeautifulSoup
from googlesearch import search

TRUSTED_SITES = [
    'amazon.com',
    'newegg.com',
    'pcworld.com',
    'techradar.com',
    'nvidia.com',
]

def is_trusted(url):
    """Check if the URL belongs to one of the trusted domains."""
    return any(trusted in url for trusted in TRUSTED_SITES)

def extract_specifications(soup):
    """
    Attempt to extract the specifications section from the parsed HTML using several heuristics.
    """
    # Heuristic 1: Look for tables with specification-like keywords
    tables = soup.find_all('table')
    for table in tables:
        text = table.get_text(separator="\n", strip=True)
        if any(kw in text.lower() for kw in ["spec", "detail", "feature"]):
            return text

    # Heuristic 2: Look for containers (div or section) whose class or id includes 'spec'
    containers = soup.find_all(
        lambda tag: tag.name in ["div", "section"] and (
            (tag.get("class") and any("spec" in c.lower() for c in tag.get("class"))) or
            (tag.get("id") and "spec" in tag.get("id").lower())
        )
    )
    for container in containers:
        text = container.get_text(separator="\n", strip=True)
        if len(text) > 100:  # arbitrary filter to avoid very short fragments
            return text

    # Heuristic 3: Search for headers that indicate a specification section
    headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    for header in headers:
        if "spec" in header.get_text(strip=True).lower():
            sibling = header.find_next_sibling()
            if sibling:
                text = sibling.get_text(separator="\n", strip=True)
                if len(text) > 100:
                    return text

    # Fallback: Return the entire page text
    return soup.get_text(separator="\n", strip=True)

def get_specifications(url):
    """Fetch the page at the URL and extract the specifications content."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        specs = extract_specifications(soup)
        return specs if specs else "No clear specification content found on this page."
    except Exception as e:
        return f"Error fetching URL ({url}): {e}"

def get_product_specs(product: str):
    """
    For each site in TRUSTED_SITES, perform a Google search restricted to that site
    and attempt to retrieve one result's specifications. Return a dictionary with
    one specification block per site.
    """
    results_dict = {}

    for site in TRUSTED_SITES:
        query = f"{product} specifications site:{site}"
        specs_found = None

        try:
            # We'll take the first valid result from that site
            search_results = search(query, stop=5)
            for url in search_results:
                specs = get_specifications(url)
                if "Error fetching URL" not in specs:
                    # If we successfully scraped specs (no error), store them
                    specs_found = f"URL: {url}\n\n{specs}"
                    break  # Stop after first successful fetch

        except Exception as e:
            specs_found = f"Error during search: {e}"

        # If we never found a successful URL or specs, store a fallback message
        if not specs_found:
            specs_found = f"No results or no valid specs found on {site}."

        # Store the results under the site name
        results_dict[site] = specs_found

    return results_dict