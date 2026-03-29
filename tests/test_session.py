"""Tests for session.py."""

from pathlib import Path

from media_backup.session import Session


class TestSessionSet:
    def test_set_returns_path_and_exists_flag(self, tmp_path):
        s = Session()
        real_dir = tmp_path / "real"
        real_dir.mkdir()

        p, exists = s.set("SSD", str(real_dir))
        assert p == real_dir
        assert exists is True

    def test_set_warns_nonexistent_path(self):
        s = Session()
        p, exists = s.set("SSD", "/nonexistent/path/xyz")
        assert exists is False

    def test_set_overwrites(self, tmp_path):
        s = Session()
        s.set("SSD", "/first")
        s.set("SSD", str(tmp_path))
        assert s.get("SSD") == tmp_path


class TestSessionUnset:
    def test_unset_existing(self):
        s = Session()
        s.set("laptop1", "/some/path")
        assert s.unset("laptop1") is True
        assert s.get("laptop1") is None

    def test_unset_nonexistent(self):
        s = Session()
        assert s.unset("nope") is False


class TestSessionResolve:
    def test_resolve_session_name(self, tmp_path):
        s = Session()
        s.set("SSD", str(tmp_path))
        label, path = s.resolve("SSD")
        assert label == "SSD"
        assert path == tmp_path

    def test_resolve_raw_path(self, tmp_path):
        s = Session()
        label, path = s.resolve(str(tmp_path))
        assert label == str(tmp_path)
        assert path == tmp_path

    def test_resolve_unknown_returns_none(self):
        s = Session()
        label, path = s.resolve("nonexistent_name_and_path")
        assert path is None


class TestSessionDrives:
    def test_has_drives_false_initially(self):
        s = Session()
        assert s.has_drives() is False
        assert set(s.missing_drives()) == {"SSD", "HDD"}

    def test_has_drives_true_when_both_set(self):
        s = Session()
        s.set("SSD", "/a")
        s.set("HDD", "/b")
        assert s.has_drives() is True
        assert s.missing_drives() == []

    def test_missing_drives_partial(self):
        s = Session()
        s.set("SSD", "/a")
        assert s.missing_drives() == ["HDD"]


class TestSessionListPaths:
    def test_required_first(self):
        s = Session()
        s.set("laptop1", "/l")
        s.set("SSD", "/s")
        s.set("HDD", "/h")
        names = [n for n, _ in s.list_paths()]
        assert names.index("SSD") < names.index("laptop1")
        assert names.index("HDD") < names.index("laptop1")

    def test_names_for_completion(self):
        s = Session()
        s.set("SSD", "/a")
        s.set("phone1", "/b")
        assert set(s.names) == {"SSD", "phone1"}
