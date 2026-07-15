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

    def test_no_version_keys_in_legacy_mode(self, sample_session: PlateSession):
        manifest = ManifestWriter(sample_session).build()
        assert "version" not in manifest
        assert "versioned_name" not in manifest

    def test_version_keys_in_shot_mode(self, sample_session: PlateSession):
        sample_session.shot = "img01_env"
        sample_session.version = 3
        manifest = ManifestWriter(sample_session).build()
        assert manifest["shot"] == "img01_env"
        assert manifest["version"] == 3
        assert manifest["versioned_name"] == "img01_env_v003"

    def test_comfy_block_none_by_default(self, sample_session: PlateSession):
        manifest = ManifestWriter(sample_session).build()
        assert manifest["comfy"] is None

    def test_comfy_block_populated(self, sample_session: PlateSession, ocio_display_transform):
        sample_session.comfy_dir = Path("/shots/test/comfy")
        sample_session.comfy_pattern = "test.%06d.png"
        sample_session.comfy_frames = 51
        sample_session.comfy_max_width = 1024
        sample_session.comfy_color_transform = ocio_display_transform

        manifest = ManifestWriter(sample_session).build()
        comfy = manifest["comfy"]
        assert comfy["dir"] == "/shots/test/comfy"
        assert comfy["pattern"] == "test.%06d.png"
        assert comfy["frames"] == 51
        assert comfy["max_width"] == 1024
        assert comfy["color_transform"]["mode"] == "ocio_display"
        assert comfy["color_transform"]["display"] == "sRGB - Display"

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
