"""Minimal anonymous OCI registry client (tag listing + digest lookup) for base-image bumps."""

from __future__ import annotations

import http.client
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from functools import lru_cache

from .proc import log

ACCEPT = ", ".join(
    [
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    ]
)


@dataclass(frozen=True)
class ImageRef:
    registry: str  # e.g. registry-1.docker.io
    repository: str  # e.g. library/golang
    tag: str | None
    digest: str | None
    original_name: str  # name as written (without tag/digest), e.g. golang

    def with_tag(self, tag: str, digest: str | None = None) -> str:
        s = f"{self.original_name}:{tag}"
        return f"{s}@{digest}" if digest else s


def parse_ref(ref: str) -> ImageRef:
    name, digest = (ref.split("@", 1) + [None])[:2]
    tag = None
    last = name.rsplit("/", 1)[-1]
    if ":" in last:
        name, tag = name.rsplit(":", 1)
    parts = name.split("/", 1)
    if len(parts) == 2 and ("." in parts[0] or ":" in parts[0] or parts[0] == "localhost"):
        registry, repo = parts
    else:
        registry, repo = "docker.io", name
    if registry == "docker.io":
        registry = "registry-1.docker.io"
        if "/" not in repo:
            repo = f"library/{repo}"
    return ImageRef(registry=registry, repository=repo, tag=tag, digest=digest, original_name=name)


class RegistryError(RuntimeError):
    pass


_tokens: dict[tuple[str, str], str] = {}
_warned: set[str] = set()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """urllib re-sends a request's headers, Authorization included, to wherever a redirect points."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_no_redirects = urllib.request.build_opener(_NoRedirect)


def _request(method: str, url: str, headers: dict[str, str], follow_redirects: bool = True) -> tuple[int, dict[str, str], bytes]:
    """(status, lower-cased headers, body). Network failures raise RegistryError, which every caller handles."""
    req = urllib.request.Request(url, method=method, headers=headers)
    try:
        with (urllib.request.urlopen(req, timeout=60) if follow_redirects else _no_redirects.open(req, timeout=60)) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()
    except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
        raise RegistryError(f"{method} {url}: {e}") from e


def _basic_auth(registry: str, realm: str) -> dict[str, str]:
    """PATCHER_REGISTRY_BASIC_AUTH ("user:token") goes only to the registry PATCHER_REGISTRY_AUTH_HOST names, and only
    when that registry's token realm is https on the same host: the registries come from upstream Dockerfiles, and an
    auth challenge can name any realm."""
    basic = os.environ.get("PATCHER_REGISTRY_BASIC_AUTH")
    if not basic:
        return {}
    host = os.environ.get("PATCHER_REGISTRY_AUTH_HOST", "")
    if not host:
        if "host" not in _warned:
            _warned.add("host")
            log("warning: PATCHER_REGISTRY_BASIC_AUTH is set without PATCHER_REGISTRY_AUTH_HOST: not sent to any registry")
        return {}
    url = urllib.parse.urlsplit(realm)
    if registry != host or url.scheme != "https" or url.netloc != host:
        return {}
    import base64

    return {"Authorization": "Basic " + base64.b64encode(basic.encode()).decode()}


def _auth_token(www_auth: str, ref: ImageRef) -> str:
    params = dict(re.findall(r'(\w+)="([^"]*)"', www_auth))
    realm = params.pop("realm", None)
    if not realm:
        raise RegistryError(f"unsupported auth challenge: {www_auth}")
    params.setdefault("scope", f"repository:{ref.repository}:pull")
    url = f"{realm}?{urllib.parse.urlencode(params)}"
    headers = _basic_auth(ref.registry, realm)
    status, _, body = _request("GET", url, headers, follow_redirects=not headers)
    if status != 200:
        raise RegistryError(f"token request failed ({status}) for {ref.repository}")
    try:
        data = json.loads(body)
    except ValueError as e:
        raise RegistryError(f"token response for {ref.repository} is not JSON") from e
    return data.get("token") or data.get("access_token")


def _call(ref: ImageRef, method: str, path: str, accept: str | None = None) -> tuple[dict[str, str], bytes]:
    url = f"https://{ref.registry}/v2/{ref.repository}/{path}"
    headers = {"Accept": accept} if accept else {}
    key = (ref.registry, ref.repository)
    if key in _tokens:
        headers["Authorization"] = f"Bearer {_tokens[key]}"
    status, resp_headers, body = _request(method, url, headers)
    if status == 401 and "www-authenticate" in resp_headers:
        _tokens[key] = _auth_token(resp_headers["www-authenticate"], ref)
        headers["Authorization"] = f"Bearer {_tokens[key]}"
        status, resp_headers, body = _request(method, url, headers)
    if status >= 400:
        raise RegistryError(f"{method} {url} -> {status}")
    return resp_headers, body


@lru_cache(maxsize=256)
def list_tags(image: str) -> tuple[str, ...]:
    ref = parse_ref(image)
    tags: list[str] = []
    path = "tags/list?n=1000"
    for _ in range(200):  # pagination guard
        headers, body = _call(ref, "GET", path)
        tags.extend(json.loads(body).get("tags") or [])
        link = headers.get("link")
        if not link:
            break
        m = re.search(r"<([^>]+)>", link)
        if not m:
            break
        nxt = m.group(1)
        path = nxt.split(f"/v2/{ref.repository}/", 1)[-1] if "/v2/" in nxt else nxt
    return tuple(tags)


@lru_cache(maxsize=512)
def digest(image: str, tag: str) -> str:
    ref = parse_ref(image)
    headers, _ = _call(ref, "HEAD", f"manifests/{tag}", accept=ACCEPT)
    d = headers.get("docker-content-digest")
    if not d:  # some registries omit it on HEAD
        headers, body = _call(ref, "GET", f"manifests/{tag}", accept=ACCEPT)
        import hashlib

        d = headers.get("docker-content-digest") or "sha256:" + hashlib.sha256(body).hexdigest()
    return d


@lru_cache(maxsize=128)
def config_labels(image: str, tag: str, platform: str = "linux/amd64") -> dict[str, str]:
    """OCI config labels of `image:tag` (for an index, the `platform` entry, else the first one)."""
    ref = parse_ref(image)
    _, body = _call(ref, "GET", f"manifests/{tag}", accept=ACCEPT)
    manifest = json.loads(body)
    if "manifests" in manifest:  # index / manifest list
        os_, arch = platform.split("/", 1)
        entries = [m for m in manifest["manifests"] if (m.get("platform") or {}).get("os") == os_
                   and (m.get("platform") or {}).get("architecture") == arch] or manifest["manifests"]
        _, body = _call(ref, "GET", f"manifests/{entries[0]['digest']}", accept=ACCEPT)
        manifest = json.loads(body)
    _, cfg = _call(ref, "GET", f"blobs/{manifest['config']['digest']}")
    return (json.loads(cfg).get("config") or {}).get("Labels") or {}
