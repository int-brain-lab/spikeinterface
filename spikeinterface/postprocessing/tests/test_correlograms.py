from typing import List
import pytest
import numpy as np

import spikeinterface.extractors as se
from spikeinterface.postprocessing import compute_correlograms

try:
    import numba
    HAVE_NUMBA = True
except ModuleNotFoundError as err:
    HAVE_NUMBA = False


def _test_correlograms(sorting, window_ms: float, bin_ms: float, methods: List[str]):
    for method in methods:
        correlograms, bins = compute_correlograms(sorting, window_ms=window_ms, bin_ms=bin_ms, symmetrize=True, 
                                                  method=method)

        if method == "numpy":
            ref_correlograms = correlograms
            ref_bins = bins
        else:
            assert np.all(correlograms == ref_correlograms), f"Failed with method={method}"
            assert np.allclose(bins, ref_bins, atol=1e-10), f"Failed with method={method}"

@pytest.mark.skip(reason="Is going to be fixed (PR #750)")
def test_compute_correlograms():
    methods = ["numpy", "auto"]
    if HAVE_NUMBA:
        methods.append("numba")

    recording, sorting = se.toy_example(num_segments=2, num_units=10, duration=100)

    _test_correlograms(sorting, window_ms=60.0, bin_ms=2.0, methods=methods)
    _test_correlograms(sorting, window_ms=43.57, bin_ms=1.6421, methods=methods)


if __name__ == '__main__':
    test_compute_correlograms()

