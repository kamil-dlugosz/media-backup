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
    def test_set_registers_path(self, _mock_render, tmp_path):
        session = Session()
        _dispatch(f"set SSD {tmp_path}", session)
        assert session.get("SSD") == tmp_path

    @patch("media_backup.repl.render_split")
    def test_unset_removes_path(self, _mock_render):
        session = Session()
        session.set("laptop1", "/some/path")
        _dispatch("unset laptop1", session)
        assert "laptop1" not in session.names

    @patch("media_backup.repl.render_split")
    def test_help_does_not_crash(self, _mock_render):
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
    def test_unknown_command(self, _mock_render):
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

    @patch("media_backup.repl.render_split")
    def test_coverage_check_with_real_dirs(self, mock_render, tmp_path):
        src = tmp_path / "src"
        tgt = tmp_path / "tgt"
        src.mkdir()
        tgt.mkdir()
        (src / "a.jpg").write_bytes(b"\x00" * 100)
        (tgt / "a.jpg").write_bytes(b"\x00" * 100)

        session = Session()
        session.set("src", str(src))
        session.set("tgt", str(tgt))
        result = _dispatch("coverage-check src tgt", session)
        assert result is True
        call_args = mock_render.call_args[0][0]
        assert any("100.0%" in str(a) for a in call_args)

    @patch("media_backup.repl.render_split")
    def test_duplicates_with_real_dir(self, mock_render, tmp_path):
        root = tmp_path / "root"
        (root / "a").mkdir(parents=True)
        (root / "b").mkdir(parents=True)
        (root / "a" / "pic.jpg").write_bytes(b"\x00" * 100)
        (root / "b" / "pic.jpg").write_bytes(b"\x00" * 100)

        session = Session()
        session.set("mydir", str(root))
        result = _dispatch("duplicates mydir", session)
        assert result is True
        call_args = mock_render.call_args[0][0]
        assert any("duplicate" in str(a).lower() for a in call_args)

    @patch("media_backup.repl.render_split")
    def test_timeline_gaps_with_real_dir(self, mock_render, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        (root / "pic.jpg").write_bytes(b"\x00" * 100)

        session = Session()
        session.set("mydir", str(root))
        result = _dispatch("timeline-gaps mydir", session)
        assert result is True
        call_args = mock_render.call_args[0][0]
        assert any("EXIF" in str(a) or "gap" in str(a).lower() or "date" in str(a).lower()
                    for a in call_args)

    @patch("media_backup.repl.render_split")
    def test_sync_check_with_real_dirs(self, mock_render, tmp_path):
        ssd = tmp_path / "ssd"
        hdd = tmp_path / "hdd"
        ssd.mkdir()
        hdd.mkdir()
        (ssd / "pic.jpg").write_bytes(b"\x00" * 100)
        (hdd / "pic.jpg").write_bytes(b"\x00" * 100)

        session = Session()
        session.set("SSD", str(ssd))
        session.set("HDD", str(hdd))
        result = _dispatch("sync-check", session)
        assert result is True
        call_args = mock_render.call_args[0][0]
        assert any("in sync" in str(a).lower() for a in call_args)

    @patch("media_backup.repl.render_split")
    def test_safe_to_clear_with_real_dirs(self, mock_render, tmp_path):
        laptop = tmp_path / "laptop"
        ssd = tmp_path / "ssd"
        hdd = tmp_path / "hdd"
        for d in (laptop, ssd, hdd):
            d.mkdir()
        (laptop / "pic.jpg").write_bytes(b"\x00" * 100)
        (ssd / "pic.jpg").write_bytes(b"\x00" * 100)
        (hdd / "pic.jpg").write_bytes(b"\x00" * 100)

        session = Session()
        session.set("SSD", str(ssd))
        session.set("HDD", str(hdd))
        session.set("laptop1", str(laptop))
        result = _dispatch("safe-to-clear laptop1", session)
        assert result is True
        call_args = mock_render.call_args[0][0]
        assert any("SAFE" in str(a) for a in call_args)
