from __future__ import annotations

from pathlib import Path

import numpy as np

from spikeinterface.core import BaseSorting, BaseSortingSegment
from spikeinterface.core.core_tools import define_function_from_class

try:
    import pandas as pd

    HAVE_PANDAS = True
except:
    HAVE_PANDAS = False
try:
    import one.alf.io as alfio
except:
    pass


class ALFSortingExtractor(BaseSorting):
    """Load ALF format data as a sorting extractor.

    Parameters
    ----------
    folder_path : str or Path
        Path to the ALF folder.
    sampling_frequency : int, default: 30000
        The sampling frequency.

    Returns
    -------
    extractor : ALFSortingExtractor
        The loaded data.
    """

    extractor_name = "ALFSorting"
    installed = HAVE_PANDAS
    installation_mesg = "To use the ALF extractors, install pandas: \n\n pip install pandas\n\n"
    name = "alf"

    def __init__(self, folder_path, sampling_frequency=30000):
        assert self.installed, self.installation_mesg
        # check correct parent folder:
        self._folder_path = Path(folder_path)
        spikes = alfio.load_object(self._folder_path, "spikes", short_keys=True)
        # TODO: is there a way to add context data to the sorting extractor?
        self.alf_clusters = alfio.load_object(self._folder_path, "clusters", short_keys=True)
        total_units = self.alf_clusters[next(iter(self.alf_clusters))].shape[0]
        unit_ids = np.arange(total_units)  # in alf format, spikes.clusters index directly into clusters
        BaseSorting.__init__(self, unit_ids=unit_ids, sampling_frequency=sampling_frequency)
        sorting_segment = ALFSortingSegment(spikes["clusters"], spikes["samples"], sampling_frequency)
        self.add_sorting_segment(sorting_segment)
        self.extra_requirements.append("pandas")
        self.extra_requirements.append("ONE-api")
        self._kwargs = {"folder_path": str(Path(folder_path).absolute()), "sampling_frequency": sampling_frequency}


class ALFSortingSegment(BaseSortingSegment):
    def __init__(self, spike_clusters, spike_samples, sampling_frequency=None):
        self._spike_clusters = spike_clusters
        self._spike_samples = spike_samples
        self._sampling_frequency = sampling_frequency
        BaseSortingSegment.__init__(self)

    def get_unit_spike_train(
        self,
        unit_id,
        start_frame,
        end_frame,
    ) -> np.ndarray:
        # must be implemented in subclass
        if start_frame is None:
            start_frame = 0
        if end_frame is None:
            end_frame = np.inf

        spike_frames = self._spike_samples[self._spike_clusters == unit_id]
        return spike_frames[(spike_frames >= start_frame) & (spike_frames < end_frame)].astype("int64", copy=False)


read_alf_sorting = define_function_from_class(source_class=ALFSortingExtractor, name="read_alf_sorting")
