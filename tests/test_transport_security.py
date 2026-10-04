"""Unit tests for the http-mode Host and Origin allowlists."""

from __future__ import annotations

from school_finance_mcp.server import browser_origins, http_transport_security


def test_localhost_always_allowed(monkeypatch):
    monkeypatch.delenv("RENDER_EXTERNAL_HOSTNAME", raising=False)
    ts = http_transport_security([])
    assert ts.enable_dns_rebinding_protection is True
    assert "127.0.0.1:*" in ts.allowed_hosts
    assert "localhost:*" in ts.allowed_hosts


def test_render_hostname_picked_up_from_env(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "example.onrender.com")
    ts = http_transport_security([])
    assert "example.onrender.com" in ts.allowed_hosts
    assert "https://example.onrender.com" in ts.allowed_origins


def test_extra_host_flag(monkeypatch):
    monkeypatch.delenv("RENDER_EXTERNAL_HOSTNAME", raising=False)
    ts = http_transport_security(["mcp.example.com"])
    assert "mcp.example.com" in ts.allowed_hosts
    assert "mcp.example.com:*" in ts.allowed_hosts


def test_cors_origin_joins_the_origin_allowlist(monkeypatch):
    monkeypatch.delenv("RENDER_EXTERNAL_HOSTNAME", raising=False)
    ts = http_transport_security([], ["https://demo.example"])
    assert "https://demo.example" in ts.allowed_origins
    assert "demo.example" not in ts.allowed_hosts


def test_browser_origins_strip_trailing_slash(monkeypatch):
    monkeypatch.delenv("RENDER_GIT_REPO_SLUG", raising=False)
    assert browser_origins(["https://demo.example/"]) == ["https://demo.example"]


def test_render_repo_owner_pages_origin_is_added(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_REPO_SLUG", "Example-Owner/some-repo")
    assert browser_origins([]) == ["https://example-owner.github.io"]
    assert browser_origins(["https://example-owner.github.io"]) == [
        "https://example-owner.github.io"
    ]


def test_wildcard_disables_protection(monkeypatch):
    monkeypatch.delenv("RENDER_EXTERNAL_HOSTNAME", raising=False)
    ts = http_transport_security(["*"])
    assert ts.enable_dns_rebinding_protection is False
