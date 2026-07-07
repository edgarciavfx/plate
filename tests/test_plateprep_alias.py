from __future__ import annotations

import plate
import plateprep


def test_plateprep_version_matches_plate():
    assert plateprep.__version__ == plate.__version__
