from __future__ import annotations

import json
from pathlib import Path

from plate.export.manifest_writer import ManifestWriter
from plate.models.frame_range import FrameRange
from plate.models.plate_session import PlateSession


class TestManifestWriter:
    def test_build_contains_expected_keys(self, sample_session: PlateSession):
        mw = ManifestWriter(sample_session)
        manifest = mw.build()
        assert manifest["shot"] == "test"
        assert manifest["source"] == str(Path("test.mov"))
        assert manifest["start_frame"] == 1001
        assert manifest["in"] == 1050
        assert manifest["out"] == 1100
        assert manifest["exported_frames"] == 0
        assert manifest["proxy"] is None
        assert manifest["exr_dir"] is None
        assert "created_at" in manifest
        assert "color_transform" in manifest

    def test_build_includes_metadata_when_present(self, sample_session: PlateSession):
        mw = ManifestWriter(sample_session)
        manifest = mw.build()
        assert manifest["fps"] == 23.976
        assert manifest["width"] == 1920
        assert manifest["codec_name"] == "h264"

    def test_build_handles_null_metadata(self, tmp_path: Path):
        session = PlateSession(
            source_path=Path("test.mov"),
            output_dir=tmp_path / "out",
            frame_range=FrameRange(1001, 1050, 1100),
        )
        mw = ManifestWriter(session)
        manifest = mw.build()
        assert "duration_seconds" not in manifest
        assert manifest["color_transform"] == {"mode": None}

    def test_build_includes_proxy_and_exr_paths(self, sample_session: PlateSession):
        sample_session.proxy_path = Path("/shots/test/proxy.mp4")
        sample_session.exr_dir = Path("/shots/test/exr")
        sample_session.exported_frames = 51
        mw = ManifestWriter(sample_session)
        manifest = mw.build()
        assert manifest["proxy"] == "/shots/test/proxy.mp4"
        assert manifest["exr_dir"] == "/shots/test/exr"
        assert manifest["exported_frames"] == 51

    def test_write_creates_file(self, sample_session: PlateSession):
        sample_session.ensure_output_dirs()
        mw = ManifestWriter(sample_session)
        path = mw.write()
        assert path.exists()
        assert path.name == "manifest.json"
        assert sample_session.manifest_path == path
        data = json.loads(path.read_text())
        assert data["shot"] == "test"

    def test_write_overwrites_existing(self, sample_session: PlateSession):
        sample_session.ensure_output_dirs()
        mw = ManifestWriter(sample_session)
        path = mw.write()
        path2 = mw.write()
        assert path == path2
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["shot"] == "test"
        assert data["in"] == 1050
