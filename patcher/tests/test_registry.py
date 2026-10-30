import urllib.error

import pytest

from patcher import registry, releases
from patcher.models import Policy

NEXUS = "nexus.example.com:8443"


@pytest.mark.parametrize("env, registry_host, realm, sent", [
    ({}, NEXUS, f"https://{NEXUS}/v2/token", False),  # nothing configured
    ({"PATCHER_REGISTRY_BASIC_AUTH": "u:t"}, NEXUS, f"https://{NEXUS}/v2/token", False),  # no host: sent nowhere
    ({"PATCHER_REGISTRY_BASIC_AUTH": "u:t", "PATCHER_REGISTRY_AUTH_HOST": NEXUS}, NEXUS, f"https://{NEXUS}/v2/token", True),
    ({"PATCHER_REGISTRY_BASIC_AUTH": "u:t", "PATCHER_REGISTRY_AUTH_HOST": NEXUS}, NEXUS, f"http://{NEXUS}/v2/token", False),
    ({"PATCHER_REGISTRY_BASIC_AUTH": "u:t", "PATCHER_REGISTRY_AUTH_HOST": NEXUS}, NEXUS, "https://evil.example/token", False),
    ({"PATCHER_REGISTRY_BASIC_AUTH": "u:t", "PATCHER_REGISTRY_AUTH_HOST": NEXUS}, "quay.io", "https://quay.io/v2/auth", False),
], ids=["unset", "no-host", "same-host", "plain-http", "foreign-realm", "other-registry"])
def test_registry_credentials_go_only_to_the_configured_host(monkeypatch, env, registry_host, realm, sent):
    """Registries come from upstream Dockerfiles, and an auth challenge can name any realm."""
    for k in ("PATCHER_REGISTRY_BASIC_AUTH", "PATCHER_REGISTRY_AUTH_HOST"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    assert bool(registry._basic_auth(registry_host, realm)) is sent


def test_the_credentialed_token_request_does_not_follow_redirects(monkeypatch):
    monkeypatch.setenv("PATCHER_REGISTRY_BASIC_AUTH", "u:t")
    monkeypatch.setenv("PATCHER_REGISTRY_AUTH_HOST", NEXUS)
    calls = []
    monkeypatch.setattr(registry, "_request", lambda method, url, headers, follow_redirects=True:
                        calls.append((headers, follow_redirects)) or (200, {}, b'{"token": "abc"}'))
    ref = registry.parse_ref(f"{NEXUS}/team/app:1.0")
    assert registry._auth_token(f'Bearer realm="https://{NEXUS}/v2/token",service="nexus"', ref) == "abc"
    assert calls == [({"Authorization": "Basic dTp0"}, False)]  # urllib would re-send it to wherever a redirect points


def test_network_errors_and_bad_token_responses_are_registry_errors(monkeypatch):
    def unreachable(req, timeout):
        raise urllib.error.URLError("connection reset by peer")

    monkeypatch.setattr(registry.urllib.request, "urlopen", unreachable)
    with pytest.raises(registry.RegistryError, match="connection reset"):  # callers catch RegistryError, not URLError
        registry._request("GET", "https://registry-1.docker.io/v2/", {})

    monkeypatch.setattr(registry, "_request", lambda *a, **k: (200, {}, b"<html>proxy login</html>"))
    with pytest.raises(registry.RegistryError, match="not JSON"):
        registry._auth_token('Bearer realm="https://auth.docker.io/token"', registry.parse_ref("alpine:3.24"))


def test_the_kev_list_applies_per_policy(monkeypatch):
    """One recipe's `kev: false` must not empty the list for the next recipe, or for a component in the same run."""
    monkeypatch.setattr(releases, "_kev", None)
    monkeypatch.setattr(releases, "load_kev", lambda: {"CVE-2026-1"})
    on = Policy(minReleaseAgeDays=7)
    off = Policy.model_validate({"minReleaseAgeDays": 7, "cooldownBypass": {"kev": False}})
    for first, second in ((off, on), (on, off)):
        monkeypatch.setattr(releases, "_kev", None)
        gates = {id(p): releases.gate_for(p) for p in (first, second)}
        assert gates[id(on)].kev == {"CVE-2026-1"} and gates[id(off)].kev == set()
