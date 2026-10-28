"""Minimal anonymous OCI registry client (tag listing + digest lookup) for base-image bumps."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from functools import lru_cache

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


def _request(method: str, url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()


def _auth_token(www_auth: str, repo: str) -> str:
    params = dict(re.findall(r'(\w+)="([^"]*)"', www_auth))
    realm = params.pop("realm", None)
    if not realm:
        raise RegistryError(f"unsupported auth challenge: {www_auth}")
    params.setdefault("scope", f"repository:{repo}:pull")
    url = f"{realm}?{urllib.parse.urlencode(params)}"
    headers = {}
    basic = os.environ.get("PATCHER_REGISTRY_BASIC_AUTH")  # optional "user:token" for private registries
    if basic:
        import base64

        headers["Authorization"] = "Basic " + base64.b64encode(basic.encode()).decode()
    status, _, body = _request("GET", url, headers)
    if status != 200:
        raise RegistryError(f"token request failed ({status}) for {repo}")
    data = json.loads(body)
    return data.get("token") or data.get("access_token")


def _call(ref: ImageRef, method: str, path: str, accept: str | None = None) -> tuple[dict[str, str], bytes]:
    url = f"https://{ref.registry}/v2/{ref.repository}/{path}"
    headers = {"Accept": accept} if accept else {}
    key = (ref.registry, ref.repository)
    if key in _tokens:
        headers["Authorization"] = f"Bearer {_tokens[key]}"
    status, resp_headers, body = _request(method, url, headers)
    if status == 401 and "www-authenticate" in resp_headers:
        _tokens[key] = _auth_token(resp_headers["www-authenticate"], ref.repository)
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
