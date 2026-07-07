from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from plate.pipeline import PlatePipeline
from plate.batch import BatchEntry, run_batch
from plate.color import ColorTransform


pytestmark = pytest.mark.integration


FOOTAGE_DIR = Path(__file__).resolve().parent.parent / "Footage"
TEST_ASSETS = Path(__file__).resolve().parent.parent / "test_assets"


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


@pytest.fixture(scope="module")
def clip() -> Path:
    path = FOOTAGE_DIR / "PF0003-02_Clip-2_REC709_2K.mov"
    if not path.exists():
        pytest.skip(f"Test footage not found: {path}")
    return path


@pytest.fixture
def small_range() -> dict:
    return {"in_frame": 1, "out_frame": 10, "start_frame": 1}


@pytest.mark.skipif(not _has_ffmpeg(), reason="ffmpeg/ffprobe not on PATH")
class TestIntegration:
    def test_basic_pipeline(self, clip: Path, tmp_path: Path, small_range: dict):
        pipeline = PlatePipeline(
            source=clip,
            output_root=tmp_path,
            **small_range,
        )
        result = pipeline.run()
        assert result.manifest_path.exists()
        manifest = json.loads(result.manifest_path.read_text())
        assert manifest["shot"] == clip.stem
        assert manifest["in"] == 1
        assert manifest["out"] == 10
        assert manifest["exported_frames"] == 10
        assert (tmp_path / clip.stem / "proxy.mp4").exists()
        exr_dir = tmp_path / clip.stem / "exr"
        assert exr_dir.exists()
        exr_files = list(exr_dir.glob("*.exr"))
        assert len(exr_files) == 10

    def test_skip_proxy(self, clip: Path, tmp_path: Path, small_range: dict):
        pipeline = PlatePipeline(
            source=clip,
            output_root=tmp_path,
            skip_proxy=True,
            **small_range,
        )
        result = pipeline.run()
        assert not (tmp_path / clip.stem / "proxy.mp4").exists()
        assert result.manifest_path.exists()

    def test_skip_exr(self, clip: Path, tmp_path: Path, small_range: dict):
        pipeline = PlatePipeline(
            source=clip,
            output_root=tmp_path,
            skip_exr=True,
            **small_range,
        )
        result = pipeline.run()
        assert (tmp_path / clip.stem / "proxy.mp4").exists()
        exr_dir = tmp_path / clip.stem / "exr"
        exr_files = list(exr_dir.glob("*.exr")) if exr_dir.exists() else []
        assert len(exr_files) == 0
        assert result.manifest_path.exists()

    def test_identity_lut(self, clip: Path, tmp_path: Path):
        pipeline = PlatePipeline(
            source=clip,
            in_frame=1,
            out_frame=5,
            start_frame=1,
            output_root=tmp_path,
            color_transform=ColorTransform(lut_path=TEST_ASSETS / "identity.cube"),
        )
        result = pipeline.run()
        assert result.manifest_path.exists()
        exr_files = list((tmp_path / clip.stem / "exr").glob("*.exr"))
        assert len(exr_files) == 5

    def test_invert_green_lut(self, clip: Path, tmp_path: Path):
        pipeline = PlatePipeline(
            source=clip,
            in_frame=1,
            out_frame=5,
            start_frame=1,
            output_root=tmp_path,
            color_transform=ColorTransform(lut_path=TEST_ASSETS / "invert_green.cube"),
        )
        result = pipeline.run()
        assert result.manifest_path.exists()
        exr_files = list((tmp_path / clip.stem / "exr").glob("*.exr"))
        assert len(exr_files) == 5

    def test_batch_mode(self, clip: Path, tmp_path: Path):
        entries = [
            BatchEntry(
                source=clip,
                in_frame=1,
                out_frame=5,
                start_frame=1,
                output_root=tmp_path,
            ),
            BatchEntry(
                source=clip,
                in_frame=10,
                out_frame=15,
                start_frame=1,
                output_root=tmp_path,
                skip_exr=True,
            ),
        ]
        results = run_batch(entries, defaults={"output_root": str(tmp_path)})
        assert len(results) == 2
        assert results[0].error is None
        assert results[1].error is None
        assert (tmp_path / clip.stem / "proxy.mp4").exists()

    def test_pipeline_with_zero_start_frame(self, clip: Path, tmp_path: Path):
        pipeline = PlatePipeline(
            source=clip,
            in_frame=0,
            out_frame=10,
            start_frame=0,
            output_root=tmp_path,
        )
        result = pipeline.run()
        assert result.manifest_path.exists()
        assert result.manifest_path.parent == tmp_path / clip.stem

    def test_batch_error_collection(self, clip: Path, tmp_path: Path):
        entries = [
            BatchEntry(
                source=clip,
                in_frame=1,
                out_frame=5,
                start_frame=1,
                output_root=tmp_path,
            ),
            BatchEntry(
                source=Path("/nonexistent/file.mov"),
                in_frame=1,
                out_frame=5,
                output_root=tmp_path,
            ),
        ]
        results = run_batch(entries, defaults={"output_root": str(tmp_path)})
        assert len(results) == 2
        assert results[0].error is None
        assert results[1].error is not None
