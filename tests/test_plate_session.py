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
