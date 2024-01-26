import pytest
import numpy as np
import pandas as pd
import shutil
import platform
from pathlib import Path

from spikeinterface.core import generate_ground_truth_recording
from spikeinterface.core import start_sorting_result
from spikeinterface.core import estimate_sparsity


if hasattr(pytest, "global_test_folder"):
    cache_folder = pytest.global_test_folder / "postprocessing"
else:
    cache_folder = Path("cache_folder") / "postprocessing"

def get_dataset():
    recording, sorting = generate_ground_truth_recording(
        durations=[30.0, 20.0], sampling_frequency=24000.0, num_channels=10, num_units=5,
        generate_sorting_kwargs=dict(firing_rates=3.0, refractory_period_ms=4.0),
        generate_unit_locations_kwargs=dict(
            margin_um=5.0,
            minimum_z=5.0,
            maximum_z=20.0,
        ),
        generate_templates_kwargs=dict(
            unit_params_range=dict(
                alpha=(9_000.0, 12_000.0),
            )
        ),
        noise_kwargs=dict(noise_level=5.0, strategy="tile_pregenerated"),
        seed=2205,
    )
    return recording, sorting

def get_sorting_result(recording, sorting, format="memory", sparsity=None, name=""):
    sparse = sparsity is not None
    if format == "memory":
        folder = None
    elif format == "binary_folder":
        folder = cache_folder / f"test_{name}_sparse{sparse}_{format}"
    elif format == "zarr":
        folder = cache_folder / f"test_{name}_sparse{sparse}_{format}.zarr"
    if folder and folder.exists():
        shutil.rmtree(folder)
    
    sortres = start_sorting_result(sorting, recording, format=format, folder=folder, sparse=False, sparsity=sparsity)

    return sortres

class ResultExtensionCommonTestSuite:
    """
    Common tests with class approach to compute extension on several cases (3 format x 2 sparsity)

    This is done a a list of differents parameters (extension_function_kwargs_list).

    This automatically precompute extension dependencies with default params before running computation.

    This also test the select_units() ability.
    """
    extension_class = None
    extension_function_kwargs_list = None
    def setUp(self):
        
        recording, sorting = get_dataset()
        # sparsity is computed once for all cases to save processing
        sparsity = estimate_sparsity(recording, sorting)

        self.sorting_results = {}
        for sparse in (True, False):
            for format in ("memory", "binary_folder", "zarr"):
                sparsity_ = sparsity if sparse else None
                sorting_result = get_sorting_result(recording, sorting, format=format, sparsity=sparsity_, name=self.extension_class.extension_name)
                key = f"sparse{sparse}_{format}"
                self.sorting_results[key] = sorting_result
    
    def tearDown(self):
        for k in list(self.sorting_results.keys()):
            sorting_result = self.sorting_results.pop(k)
            if sorting_result.format != "memory":
                folder = sorting_result.folder
                del sorting_result
                shutil.rmtree(folder)

    @property
    def extension_name(self):
        return self.extension_class.extension_name

    def _check_one(self, sorting_result):
        sorting_result.select_random_spikes(max_spikes_per_unit=50, seed=2205)

        for dependency_name in self.extension_class.depend_on:
            if "|" in dependency_name:
                dependency_name = dependency_name.split("|")[0]
            sorting_result.compute(dependency_name)

        
        for kwargs in self.extension_function_kwargs_list:
            print('  kwargs', kwargs)
            sorting_result.compute(self.extension_name, **kwargs)
        ext = sorting_result.get_extension(self.extension_name)
        assert ext is not None
        assert len(ext.data) > 0
        
        some_unit_ids = sorting_result.unit_ids[::2]
        sliced = sorting_result.select_units(some_unit_ids, format="memory")
        assert np.array_equal(sliced.unit_ids, sorting_result.unit_ids[::2])
        # print(sliced)


    def test_extension(self):

        for key, sorting_result in self.sorting_results.items():
            print()
            print(self.extension_name, key)
            self._check_one(sorting_result)
