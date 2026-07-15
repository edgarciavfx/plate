"""ColorTransform — describes an optional color transform to apply during
EXR export, and a helper to resolve it to a .cube LUT file.

Three modes are supported:
  - lut_path: a .cube file applied directly via FFmpeg's lut3d filter.
  - ocio_config + src/dst colorspace: baked to a temp .cube via PyOpenColorIO,
    then applied the same way. opencolorio is an optional dependency; an
    ImportError with a clear install hint is raised if it is missing.
  - ocio_config + src colorspace + display/view: bakes an OCIO display/view
    transform (display-referred output, e.g. for ComfyUI). Requires
    OpenColorIO >= 2.0.

Note that FFmpeg decodes the source with no color management: the baked
LUT's input space is whatever the caller declares as src_colorspace. Plate
trusts that declaration; it cannot validate it against the footage.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ColorTransform:
    lut_path: Optional[Path] = None
    ocio_config: Optional[Path] = None
    src_colorspace: Optional[str] = None
    dst_colorspace: Optional[str] = None
    display: Optional[str] = None
    view: Optional[str] = None

    def is_active(self) -> bool:
        return self.lut_path is not None or self.ocio_config is not None

    def is_display_view(self) -> bool:
        return self.display is not None

    @classmethod
    def from_options(
        cls,
        lut_path: str | Path | None = None,
        ocio_config: str | Path | None = None,
        ocio_src: str | None = None,
        ocio_dst: str | None = None,
        ocio_display: str | None = None,
        ocio_view: str | None = None,
    ) -> ColorTransform:
        has_lut = lut_path is not None
        has_ocio = ocio_config is not None
        has_ocio_src = ocio_src is not None
        has_ocio_dst = ocio_dst is not None
        has_display = ocio_display is not None
        has_view = ocio_view is not None

        if has_lut and has_ocio:
            raise ValueError("lut_path and ocio_config are mutually exclusive.")
        if has_display != has_view:
            raise ValueError("ocio_display and ocio_view must be set together.")
        if has_display and has_ocio_dst:
            raise ValueError(
                "ocio_dst and ocio_display/ocio_view are mutually exclusive."
            )
        if (has_ocio_src or has_ocio_dst or has_display) and not has_ocio:
            raise ValueError(
                "ocio_src, ocio_dst and ocio_display/ocio_view require ocio_config."
            )
        if has_ocio and not (has_ocio_src and (has_ocio_dst or has_display)):
            raise ValueError(
                "ocio_config requires ocio_src plus either ocio_dst or "
                "ocio_display/ocio_view."
            )

        if has_lut:
            return cls(lut_path=Path(lut_path))
        if has_ocio:
            return cls(
                ocio_config=Path(ocio_config),
                src_colorspace=ocio_src,
                dst_colorspace=ocio_dst,
                display=ocio_display,
                view=ocio_view,
            )
        return cls()

    def to_dict(self) -> dict:
        if self.lut_path is not None:
            return {"mode": "lut", "lut_path": str(self.lut_path)}
        if self.ocio_config is not None:
            if self.is_display_view():
                return {
                    "mode": "ocio_display",
                    "ocio_config": str(self.ocio_config),
                    "src_colorspace": self.src_colorspace,
                    "display": self.display,
                    "view": self.view,
                }
            return {
                "mode": "ocio",
                "ocio_config": str(self.ocio_config),
                "src_colorspace": self.src_colorspace,
                "dst_colorspace": self.dst_colorspace,
            }
        return {"mode": None}


def bake_to_cube(transform: ColorTransform, tmp_dir: str | Path) -> Path:
    """Return the .cube path to pass to FFmpeg's lut3d filter.

    For a lut_path transform, validates the file exists and returns it.
    For an OCIO transform, bakes the colorspace conversion to a new .cube
    file inside tmp_dir and returns that path.
    """
    if transform.lut_path is not None:
        lut = Path(transform.lut_path)
        if not lut.exists():
            raise FileNotFoundError(f"LUT file not found: {lut}")
        return lut

    if transform.ocio_config is not None:
        ocio_path = Path(transform.ocio_config)
        if not ocio_path.exists():
            raise FileNotFoundError(f"OCIO config not found: {ocio_path}")

        try:
            import PyOpenColorIO as ocio
        except ImportError:
            raise ImportError(
                "The 'opencolorio' package is required for OCIO config support. "
                "Install it with: pip install opencolorio"
            )

        config = ocio.Config.CreateFromFile(str(ocio_path))
        cube_path = Path(tmp_dir) / "plate_ocio_baked.cube"

        baker = ocio.Baker()
        baker.setConfig(config)
        baker.setFormat("iridas_cube")
        baker.setInputSpace(transform.src_colorspace)
        if transform.is_display_view():
            if not hasattr(baker, "setDisplayView"):
                raise RuntimeError(
                    "Baking an OCIO display/view transform requires "
                    "OpenColorIO >= 2.0. Upgrade with: pip install -U opencolorio"
                )
            baker.setDisplayView(transform.display, transform.view)
        else:
            baker.setTargetSpace(transform.dst_colorspace)
        baker.setCubeSize(33)
        baker.bake(str(cube_path))

        return cube_path

    raise ValueError("ColorTransform has no lut_path or ocio_config set.")
