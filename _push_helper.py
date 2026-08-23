#!/usr/bin/env python3
"""Create a GitHub repo under owner Ansygroup using the stored git credential.
Reads the credential from git's store (never prints the token)."""
import subprocess, json, urllib.request, base64, os


def _token():
    # git credential store -> find github.com entry
    out = subprocess.run(["git", "credential", "fill"],
                         input=b"protocol=https\nhost=github.com\n",
                         capture_output=True).stdout.decode()
    for line in out.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    return None


def _api(token, path, data=None, method="GET"):
    url = "https://api.github.com" + path
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "autopilot-os")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def api_login():
    t = _token()
    if not t:
        raise RuntimeError("no stored github credential")
    return _api(t, "/user")["login"]


def create_repo(name, private=False):
    """Create a GitHub repo. On a name clash (422) retry with a short
    timestamp suffix so AUTO publishing never fails on an existing repo."""
    import time
    t = _token()
    if not t:
        raise RuntimeError("no stored github credential")
    repo = None
    try:
        repo = _api(t, "/user/repos", {"name": name, "private": private, "auto_init": False}, "POST")
    except urllib.error.HTTPError as e:
        if e.code == 422:  # name already exists
            suffix = str(int(time.time()))[-5:]
            repo = _api(t, "/user/repos", {"name": "%s-%s" % (name, suffix), "private": private, "auto_init": False}, "POST")
        else:
            raise
    return repo


def enable_pages(full_name):
    """Enable GitHub Pages (public, served from main:/) and return the live URL.
    Must be called AFTER the branch is pushed (branch must exist)."""
    t = _token()
    if not t:
        raise RuntimeError("no stored github credential")
    pages = _api(t, "/repos/%s/pages" % full_name, {"source": {"branch": "main", "path": "/"}}, "POST")
    return pages.get("html_url")
