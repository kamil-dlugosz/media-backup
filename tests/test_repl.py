"""Tests for repl.py command dispatch."""

from unittest.mock import patch

from media_backup.repl import _dispatch, _parse_min_gap
from media_backup.session import Session


class TestParseMinGap:
    def test_default(self):
        val, remaining = _parse_min_gap(["SSD"])
        assert val == 7
        assert remaining == ["SSD"]

    def test_explicit(self):
        val, remaining = _parse_min_gap(["SSD", "--min-gap", "14"])
        assert val == 14
        assert remaining == ["SSD"]

    def test_negative_ignored(self):
        val, remaining = _parse_min_gap(["SSD", "--min-gap", "-5"])
        assert val == 7
        assert remaining == ["SSD"]

    def test_zero_ignored(self):
        val, remaining = _parse_min_gap(["SSD", "--min-gap", "0"])
        assert val == 7
        assert remaining == ["SSD"]

    def test_non_numeric_ignored(self):
        val, remaining = _parse_min_gap(["SSD", "--min-gap", "abc"])
        assert val == 7
        assert remaining == ["SSD"]


class TestDispatch:
    @patch("media_backup.repl.render_split")
    def test_set_registers_path(self, mock_render, tmp_path):
        session = Session()
        _dispatch(f"set SSD {tmp_path}", session)
        assert session.get("SSD") == tmp_path

    @patch("media_backup.repl.render_split")
    def test_unset_removes_path(self, mock_render):
        session = Session()
        session.set("laptop1", "/some/path")
        _dispatch("unset laptop1", session)
        assert "laptop1" not in session.names

    @patch("media_backup.repl.render_split")
    def test_help_does_not_crash(self, mock_render):
        session = Session()
        result = _dispatch("help", session)
        assert result is True

    def test_quit_returns_false(self):
        session = Session()
        result = _dispatch("quit", session)
        assert result is False

    def test_exit_returns_false(self):
        session = Session()
        result = _dispatch("exit", session)
        assert result is False

    @patch("media_backup.repl.render_split")
    def test_unknown_command(self, mock_render):
        session = Session()
        result = _dispatch("foobar", session)
        assert result is True

    @patch("media_backup.repl.render_split")
    def test_sync_check_without_drives_shows_error(self, mock_render):
        session = Session()
        result = _dispatch("sync-check", session)
        assert result is True
        call_args = mock_render.call_args[0][0]
        assert any("not set" in str(a) for a in call_args)

    @patch("media_backup.repl.render_split")
    def test_safe_to_clear_without_drives_shows_error(self, mock_render):
        session = Session()
        result = _dispatch("safe-to-clear laptop1", session)
        assert result is True
        call_args = mock_render.call_args[0][0]
        assert any("not set" in str(a) for a in call_args)
