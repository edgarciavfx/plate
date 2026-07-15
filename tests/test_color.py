from __future__ import annotations

from pathlib import Path

import pytest

from plate.color import ColorTransform, bake_to_cube


class TestColorTransform:
    def test_inactive_by_default(self, empty_color_transform: ColorTransform):
        assert empty_color_transform.is_active() is False

    def test_active_with_lut(self, lut_color_transform: ColorTransform):
        assert lut_color_transform.is_active() is True

    def test_active_with_ocio(self, ocio_color_transform: ColorTransform):
        assert ocio_color_transform.is_active() is True

    def test_to_dict_lut_mode(self, lut_color_transform: ColorTransform):
        d = lut_color_transform.to_dict()
        assert d["mode"] == "lut"
        assert d["lut_path"] == "/some/lut.cube"

    def test_to_dict_ocio_mode(self, ocio_color_transform: ColorTransform):
        d = ocio_color_transform.to_dict()
        assert d["mode"] == "ocio"
        assert d["ocio_config"] == "/some/config.ocio"
        assert d["src_colorspace"] == "log"
        assert d["dst_colorspace"] == "linear"

    def test_to_dict_none_mode(self, empty_color_transform: ColorTransform):
        d = empty_color_transform.to_dict()
        assert d == {"mode": None}


class TestFromOptions:
    def test_no_options_returns_inactive(self):
        ct = ColorTransform.from_options()
        assert ct.is_active() is False

    def test_lut_only(self):
        ct = ColorTransform.from_options(lut_path="/some/lut.cube")
        assert ct.is_active() is True
        assert ct.lut_path == Path("/some/lut.cube")

    def test_ocio_only(self):
        ct = ColorTransform.from_options(
            ocio_config="/some/config.ocio",
            ocio_src="log",
            ocio_dst="linear",
        )
        assert ct.is_active() is True
        assert ct.ocio_config == Path("/some/config.ocio")
        assert ct.src_colorspace == "log"
        assert ct.dst_colorspace == "linear"

    def test_lut_and_ocio_mutually_exclusive(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            ColorTransform.from_options(
                lut_path="/some/lut.cube",
                ocio_config="/some/config.ocio",
            )

    def test_ocio_src_without_config_raises(self):
        with pytest.raises(ValueError, match="require ocio_config"):
            ColorTransform.from_options(ocio_src="log")

    def test_ocio_dst_without_config_raises(self):
        with pytest.raises(ValueError, match="require ocio_config"):
            ColorTransform.from_options(ocio_dst="linear")

    def test_ocio_config_without_src_and_dst_raises(self):
        with pytest.raises(ValueError, match="requires ocio_src"):
            ColorTransform.from_options(ocio_config="/some/config.ocio")

    def test_ocio_config_with_src_only_raises(self):
        with pytest.raises(ValueError, match="requires ocio_src"):
            ColorTransform.from_options(
                ocio_config="/some/config.ocio",
                ocio_src="log",
            )

    def test_display_view(self):
        ct = ColorTransform.from_options(
            ocio_config="/some/config.ocio",
            ocio_src="log",
            ocio_display="sRGB - Display",
            ocio_view="ACES 1.0 - SDR Video",
        )
        assert ct.is_active() is True
        assert ct.is_display_view() is True
        assert ct.display == "sRGB - Display"
        assert ct.view == "ACES 1.0 - SDR Video"
        assert ct.dst_colorspace is None

    def test_display_without_view_raises(self):
        with pytest.raises(ValueError, match="must be set together"):
            ColorTransform.from_options(
                ocio_config="/some/config.ocio",
                ocio_src="log",
                ocio_display="sRGB - Display",
            )

    def test_view_without_display_raises(self):
        with pytest.raises(ValueError, match="must be set together"):
            ColorTransform.from_options(
                ocio_config="/some/config.ocio",
                ocio_src="log",
                ocio_view="Standard",
            )

    def test_display_and_dst_mutually_exclusive(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            ColorTransform.from_options(
                ocio_config="/some/config.ocio",
                ocio_src="log",
                ocio_dst="linear",
                ocio_display="sRGB - Display",
                ocio_view="Standard",
            )

    def test_display_without_config_raises(self):
        with pytest.raises(ValueError, match="require ocio_config"):
            ColorTransform.from_options(
                ocio_display="sRGB - Display",
                ocio_view="Standard",
            )

    def test_display_without_src_raises(self):
        with pytest.raises(ValueError, match="requires ocio_src"):
            ColorTransform.from_options(
                ocio_config="/some/config.ocio",
                ocio_display="sRGB - Display",
                ocio_view="Standard",
            )

    def test_to_dict_display_mode(self):
        ct = ColorTransform.from_options(
            ocio_config="/some/config.ocio",
            ocio_src="log",
            ocio_display="sRGB - Display",
            ocio_view="Standard",
        )
        d = ct.to_dict()
        assert d["mode"] == "ocio_display"
        assert d["ocio_config"] == "/some/config.ocio"
        assert d["src_colorspace"] == "log"
        assert d["display"] == "sRGB - Display"
        assert d["view"] == "Standard"
        assert "dst_colorspace" not in d


class TestBakeToCube:
    def test_lut_path_returns_path(self, tmp_path: Path):
        cube = tmp_path / "test.cube"
        cube.write_text("LUT_3D_SIZE 2\n")
        ct = ColorTransform(lut_path=cube)
        result = bake_to_cube(ct, tmp_path)
        assert result == cube

    def test_lut_path_not_found_raises(self):
        ct = ColorTransform(lut_path=Path("/nonexistent/lut.cube"))
        with pytest.raises(FileNotFoundError, match="LUT file not found"):
            bake_to_cube(ct, "/tmp")

    def test_ocio_config_not_found_raises(self):
        ct = ColorTransform(
            ocio_config=Path("/nonexistent/config.ocio"),
            src_colorspace="log",
            dst_colorspace="linear",
        )
        with pytest.raises(FileNotFoundError, match="OCIO config not found"):
            bake_to_cube(ct, "/tmp")

    def test_inactive_transform_raises_value_error(self, empty_color_transform: ColorTransform):
        with pytest.raises(ValueError, match="no lut_path or ocio_config"):
            bake_to_cube(empty_color_transform, "/tmp")

    def _fake_ocio(self, mocker, baker=None):
        """Build a fake PyOpenColorIO module and register it in sys.modules."""
        import sys
        fake = mocker.MagicMock()
        if baker is not None:
            fake.Baker.return_value = baker
        mocker.patch.dict(sys.modules, {"PyOpenColorIO": fake})
        return fake

    def test_display_view_uses_set_display_view(self, mocker, tmp_path: Path):
        ocio_cfg = tmp_path / "config.ocio"
        ocio_cfg.write_text("ocio_profile_version: 2\n")
        ct = ColorTransform(
            ocio_config=ocio_cfg,
            src_colorspace="log",
            display="sRGB - Display",
            view="Standard",
        )
        fake = self._fake_ocio(mocker)
        baker = fake.Baker.return_value

        result = bake_to_cube(ct, tmp_path)

        baker.setInputSpace.assert_called_once_with("log")
        baker.setDisplayView.assert_called_once_with("sRGB - Display", "Standard")
        baker.setTargetSpace.assert_not_called()
        assert result == tmp_path / "plate_ocio_baked.cube"

    def test_colorspace_mode_uses_set_target_space(self, mocker, tmp_path: Path):
        ocio_cfg = tmp_path / "config.ocio"
        ocio_cfg.write_text("ocio_profile_version: 2\n")
        ct = ColorTransform(
            ocio_config=ocio_cfg,
            src_colorspace="log",
            dst_colorspace="linear",
        )
        fake = self._fake_ocio(mocker)
        baker = fake.Baker.return_value

        bake_to_cube(ct, tmp_path)

        baker.setTargetSpace.assert_called_once_with("linear")
        baker.setDisplayView.assert_not_called()

    def test_display_view_requires_ocio_v2(self, mocker, tmp_path: Path):
        ocio_cfg = tmp_path / "config.ocio"
        ocio_cfg.write_text("ocio_profile_version: 1\n")
        ct = ColorTransform(
            ocio_config=ocio_cfg,
            src_colorspace="log",
            display="sRGB - Display",
            view="Standard",
        )

        class _V1Baker:
            def setConfig(self, config): pass
            def setFormat(self, fmt): pass
            def setInputSpace(self, space): pass
            def setTargetSpace(self, space): pass
            def setCubeSize(self, size): pass
            def bake(self, path): pass

        self._fake_ocio(mocker, baker=_V1Baker())
        with pytest.raises(RuntimeError, match="OpenColorIO >= 2.0"):
            bake_to_cube(ct, tmp_path)

    def test_ocio_import_error_when_not_installed(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        ocio_cfg = tmp_path / "config.ocio"
        ocio_cfg.write_text("ocio_profile_version: 2\n")
        ct = ColorTransform(
            ocio_config=ocio_cfg,
            src_colorspace="log",
            dst_colorspace="linear",
        )
        monkeypatch.setattr("builtins.__import__", lambda name, *a, **kw: (_ for _ in ()).throw(ImportError("no ocio")))
        with pytest.raises(ImportError, match="opencolorio"):
            bake_to_cube(ct, tmp_path)
