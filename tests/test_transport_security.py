"""Unit tests for the http-mode Host allowlist."""

from __future__ import annotations

from school_finance_mcp.server import http_transport_security


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


def test_wildcard_disables_protection(monkeypatch):
    monkeypatch.delenv("RENDER_EXTERNAL_HOSTNAME", raising=False)
    ts = http_transport_security(["*"])
    assert ts.enable_dns_rebinding_protection is False
