from __future__ import annotations

from pathlib import Path

from plate.models.frame_range import FrameRange
from plate.models.plate_session import PlateSession


class TestPlateSession:
    def test_shot_name_uses_source_stem(self):
        session = PlateSession(
            source_path=Path("/some/path/my_clip.mov"),
            output_dir=Path("/out"),
            frame_range=FrameRange(1001, 1050, 1100),
        )
        assert session.shot_name == "my_clip"

    def test_shot_name_without_extension(self):
        session = PlateSession(
            source_path=Path("clip.mov"),
            output_dir=Path("/out"),
            frame_range=FrameRange(1001, 1050, 1100),
        )
        assert session.shot_name == "clip"

    def test_path_coercion_in_post_init(self):
        session = PlateSession(
            source_path="some/file.mov",
            output_dir="/tmp/output",
            frame_range=FrameRange(1001, 1050, 1100),
        )
        assert isinstance(session.source_path, Path)
        assert isinstance(session.output_dir, Path)
        assert session.source_path == Path("some/file.mov")

    def test_ensure_output_dirs_creates_directories(self, tmp_path):
        session = PlateSession(
            source_path=Path("test.mov"),
            output_dir=tmp_path / "shots" / "test",
            frame_range=FrameRange(1001, 1050, 1100),
        )
        session.ensure_output_dirs()
        assert (tmp_path / "shots" / "test").exists()
        assert (tmp_path / "shots" / "test" / "exr").exists()
        assert session.exr_dir == tmp_path / "shots" / "test" / "exr"

    def test_ensure_output_dirs_is_idempotent(self, tmp_path):
        session = PlateSession(
            source_path=Path("test.mov"),
            output_dir=tmp_path / "shots" / "test",
            frame_range=FrameRange(1001, 1050, 1100),
        )
        session.ensure_output_dirs()
        session.ensure_output_dirs()  # should not raise
        assert session.exr_dir.exists()

    def test_default_field_values(self):
        session = PlateSession(
            source_path=Path("test.mov"),
            output_dir=Path("/out"),
            frame_range=FrameRange(1001, 1050, 1100),
        )
        assert session.metadata is None
        assert session.exr_dir is None
        assert session.proxy_path is None
        assert session.manifest_path is None
        assert session.exported_frames == 0
        assert session.color_transform is None

    def test_session_with_metadata(self, sample_metadata, sample_frame_range, tmp_path):
        session = PlateSession(
            source_path=Path("test.mov"),
            output_dir=tmp_path / "out",
            frame_range=sample_frame_range,
            metadata=sample_metadata,
        )
        assert session.metadata is sample_metadata
        assert session.metadata.fps == 23.976


def _make_session(**kwargs) -> PlateSession:
    defaults = dict(
        source_path=Path("/footage/my_clip.mov"),
        output_dir=Path("/shots/img01_env"),
        frame_range=FrameRange(1001, 1050, 1100),
    )
    defaults.update(kwargs)
    return PlateSession(**defaults)


class TestLegacyModeProperties:
    def test_shot_mode_false(self):
        assert _make_session().shot_mode is False

    def test_versioned_name_none(self):
        assert _make_session().versioned_name is None

    def test_frame_base_name_is_stem(self):
        assert _make_session().frame_base_name == "my_clip"

    def test_plates_dir(self):
        assert _make_session().plates_dir == Path("/shots/img01_env/exr")

    def test_comfy_export_dir(self):
        assert _make_session().comfy_export_dir == Path("/shots/img01_env/comfy")

    def test_proxy_filename(self):
        assert _make_session().proxy_filename == "proxy.mp4"

    def test_nuke_script_path(self):
        assert _make_session().nuke_script_path == Path("/shots/img01_env/my_clip.nk")


class TestShotModeProperties:
    def _session(self) -> PlateSession:
        return _make_session(shot="img01_env", version=2)

    def test_shot_mode_true(self):
        assert self._session().shot_mode is True

    def test_shot_name_uses_shot(self):
        assert self._session().shot_name == "img01_env"

    def test_versioned_name(self):
        assert self._session().versioned_name == "img01_env_v002"

    def test_frame_base_name(self):
        assert self._session().frame_base_name == "img01_env_v002"

    def test_plates_dir(self):
        assert self._session().plates_dir == Path(
            "/shots/img01_env/plates/img01_env_v002"
        )

    def test_comfy_export_dir(self):
        assert self._session().comfy_export_dir == Path(
            "/shots/img01_env/comfy/img01_env_v002"
        )

    def test_proxy_filename(self):
        assert self._session().proxy_filename == "proxy_v002.mp4"

    def test_nuke_script_path(self):
        assert self._session().nuke_script_path == Path(
            "/shots/img01_env/nuke/img01_env_v002.nk"
        )

    def test_default_version_is_1(self):
        session = _make_session(shot="img01_env")
        assert session.versioned_name == "img01_env_v001"


class TestEnsureOutputDirsShotMode:
    def test_scaffolds_and_creates_plates_version_dir(self, tmp_path):
        session = _make_session(
            output_dir=tmp_path / "shots" / "img01_env",
            shot="img01_env",
            version=1,
        )
        session.ensure_output_dirs()
        shot_dir = tmp_path / "shots" / "img01_env"
        for folder in ("ref", "comfy", "paint", "nuke", "renders", "breakdown", "plates"):
            assert (shot_dir / folder).is_dir()
        assert session.exr_dir == shot_dir / "plates" / "img01_env_v001"
        assert session.exr_dir.is_dir()

    def test_custom_scaffold_folders(self, tmp_path):
        session = _make_session(
            output_dir=tmp_path / "shots" / "img01_env",
            shot="img01_env",
        )
        session.ensure_output_dirs(scaffold_folders=["ref", "plates"])
        shot_dir = tmp_path / "shots" / "img01_env"
        assert (shot_dir / "ref").is_dir()
        assert not (shot_dir / "paint").exists()
        assert session.exr_dir.is_dir()
