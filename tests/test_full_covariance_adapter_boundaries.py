from __future__ import annotations

import pandas as pd
import pytest

from gazeforge.location_scale_hierarchical_bootstrap import (
    LocationScaleHierarchicalBootstrapSpec,
    bootstrap_location_scale_hierarchy,
)
from gazeforge.location_scale_refit_residual_calibration import (
    LocationScaleRefitResidualCalibrationSpec,
    calibrate_location_scale_residuals_with_refits,
)
from gazeforge.location_scale_residual_calibration import (
    LocationScaleResidualCalibrationSpec,
    calibrate_location_scale_residuals,
)


def test_uncertainty_adapters_do_not_silently_accept_new_model_family() -> None:
    unsupported_result = object()
    empty_data = pd.DataFrame()

    with pytest.raises(TypeError):
        calibrate_location_scale_residuals(
            unsupported_result,
            empty_data,
            spec=LocationScaleResidualCalibrationSpec(n_simulations=50, seed=7001),
        )
    with pytest.raises(TypeError):
        calibrate_location_scale_residuals_with_refits(
            unsupported_result,
            empty_data,
            spec=LocationScaleRefitResidualCalibrationSpec(n_simulations=2, seed=7002),
        )
    with pytest.raises(TypeError):
        bootstrap_location_scale_hierarchy(
            unsupported_result,
            empty_data,
            spec=LocationScaleHierarchicalBootstrapSpec(n_simulations=2, seed=7003),
        )
