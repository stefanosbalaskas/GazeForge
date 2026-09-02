import pandas as pd
import pytest

from gazeforge import DynamicAOIKeyframe, dynamic_aois_from_frame, dynamic_aois_to_frame
from gazeforge.exceptions import SchemaError


def test_dynamic_aoi_table_roundtrip_preserves_provenance():
    original = [
        DynamicAOIKeyframe("a", "target", 0, 0, 0, 10, 10, source="human"),
        DynamicAOIKeyframe("a", "target", 100, 1, 0, 11, 10, source="human"),
    ]
    restored = dynamic_aois_from_frame(dynamic_aois_to_frame(original))
    assert restored == original


def test_dynamic_aoi_table_rejects_duplicate_track_timestamps():
    table = dynamic_aois_to_frame(
        [DynamicAOIKeyframe("a", "target", 0, 0, 0, 10, 10)]
    )
    duplicate = pd.concat([table, table], ignore_index=True)
    with pytest.raises(SchemaError, match="duplicate"):
        dynamic_aois_from_frame(duplicate)
