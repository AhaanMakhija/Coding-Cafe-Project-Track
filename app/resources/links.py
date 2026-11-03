"""Describing saved links, so the library can say where a link goes before you click it."""

from urllib.parse import urlsplit

# Domain -> friendly name. A link matches a domain or any of its subdomains
# (docs.google.com matches google.com), but never a look-alike such as
# notyoutube.com.
KNOWN_SITES = {
    "drive.google.com": "Google Drive",
    "docs.google.com": "Google Docs",
    "onedrive.live.com": "OneDrive",
    "1drv.ms": "OneDrive",
    "sharepoint.com": "OneDrive",
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "github.com": "GitHub",
    "dropbox.com": "Dropbox",
}


def link_source(url):
    """Friendly name for where a link points.

    >>> link_source("https://drive.google.com/drive/folders/abc")
    'Google Drive'
    >>> link_source("https://www.example.com/page")
    'example.com'
    """
    host = (urlsplit(url or "").hostname or "").lower()
    if not host:
        return ""
    for domain, name in KNOWN_SITES.items():
        if host == domain or host.endswith("." + domain):
            return name
    return host.removeprefix("www.")
