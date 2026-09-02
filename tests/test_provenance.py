import json

import pandas as pd

from gazeforge import AuditTrail, ModelCard, build_audit_report, fingerprint_frame


def test_fingerprint_changes_with_data():
    a = pd.DataFrame({"x": [1, 2]})
    b = pd.DataFrame({"x": [1, 3]})
    assert fingerprint_frame(a) != fingerprint_frame(b)


def test_audit_trail_and_report_are_serialisable():
    a = pd.DataFrame({"x": [1, 2]})
    b = a.assign(y=[3, 4])
    trail = AuditTrail()
    trail.add(operation="test", input_data=a, output_data=b, parameters={"alpha": 1})
    card = ModelCard(
        name="model",
        version="1",
        task="test",
        intended_use="unit tests",
        limitations=["not a scientific model"],
    )
    report = build_audit_report(b, trail=trail, model_cards=[card])
    encoded = json.dumps(report)
    assert "fingerprint_sha256" in encoded
    assert report["operations"][0]["operation"] == "test"
