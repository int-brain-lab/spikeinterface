from re import escape
from unittest import TestCase, mock

import numpy as np
from numpy.testing import assert_array_equal
import pytest
import requests

from spikeinterface.extractors import IblRecordingExtractor, read_ibl_sorting
from spikeinterface.extractors import read_ibl_sorting
from spikeinterface.core import generate_sorting

EID = "e2b845a1-e313-4a08-bc61-a5f662ed295e"
PID = "80f6ffdd-f692-450f-ab19-cd6d45bfd73e"


@pytest.mark.streaming_extractors
class TestDefaultIblRecordingExtractorApBand(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = EID
        try:
            cls.recording = IblRecordingExtractor(session=cls.session, stream_name="probe00.ap")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 503:
                pytest.skip("Skipping test due to server being down (HTTP 503).")
            else:
                raise
        except KeyError as e:
            # This is another error which I think is caused by server problems. I think that ONE is not handling their
            # Exceptions properly so this is a workaround.
            expected_error_message = "None of [Index(['e2b845a1-e313-4a08-bc61-a5f662ed295e', '012bf9d0-765c-4743-81da-4f8db39c9a19'], dtype='object')] are in the [index]"
            if str(e) == expected_error_message:
                pytest.skip(f"Skipping test due to KeyError: {e}")
            else:
                raise
        cls.small_scaled_trace = cls.recording.get_traces(start_frame=5, end_frame=26, return_scaled=True)
        cls.small_unscaled_trace = cls.recording.get_traces(
            start_frame=5, end_frame=26
        )  # return_scaled=False is SI default

    def test_get_stream_names(self):
        stream_names = IblRecordingExtractor.get_stream_names(session=self.session)

        expected_stream_names = ["probe01.ap", "probe01.lf", "probe00.ap", "probe00.lf"]
        self.assertCountEqual(first=stream_names, second=expected_stream_names)

    def test_dtype(self):
        expected_datatype = "int16"
        assert self.recording.get_dtype().name == expected_datatype

    def test_channel_ids(self):
        expected_channel_ids = [f"AP{index}" for index in range(384)]
        self.assertListEqual(list1=list(self.recording.get_channel_ids()), list2=expected_channel_ids)

    def test_gains(self):
        expected_gains = 2.34375 * np.ones(shape=384)
        assert_array_equal(x=self.recording.get_channel_gains(), y=expected_gains)

    def test_offsets(self):
        expected_offsets = np.zeros(shape=384)
        assert_array_equal(x=self.recording.get_channel_offsets(), y=expected_offsets)

    def test_probe_representation(self):
        probe = self.recording.get_probe()
        expected_probe_representation = "Probe - 384ch - 1shanks"
        assert repr(probe) == expected_probe_representation

    def test_property_keys(self):
        expected_property_keys = [
            "gain_to_uV",
            "offset_to_uV",
            "contact_vector",
            "location",
            "group",
            "shank",
            "shank_row",
            "shank_col",
            "good_channel",
            "inter_sample_shift",
            "adc",
            "index_on_probe",
        ]
        self.assertCountEqual(first=self.recording.get_property_keys(), second=expected_property_keys)

    def test_trace_shape(self):
        expected_shape = (21, 384)
        self.assertTupleEqual(tuple1=self.small_scaled_trace.shape, tuple2=expected_shape)

    def test_scaled_trace_dtype(self):
        expected_dtype = np.dtype("float32")
        assert self.small_scaled_trace.dtype == expected_dtype

    def test_unscaled_trace_dtype(self):
        expected_dtype = np.dtype("int16")
        assert self.small_unscaled_trace.dtype == expected_dtype


@pytest.mark.streaming_extractors
class TestIblStreamingRecordingExtractorApBandWithLoadSyncChannel(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = "e2b845a1-e313-4a08-bc61-a5f662ed295e"
        cls.recording = IblRecordingExtractor(session=cls.session, stream_name="probe00.ap", load_sync_channel=True)
        cls.small_scaled_trace = cls.recording.get_traces(start_frame=5, end_frame=26, return_scaled=True)
        cls.small_unscaled_trace = cls.recording.get_traces(
            start_frame=5, end_frame=26
        )  # return_scaled=False is SI default

    def test_dtype(self):
        expected_datatype = "int16"
        assert self.recording.get_dtype().name == expected_datatype

    def test_channel_ids(self):
        expected_channel_ids = [f"AP{index}" for index in range(384)] + ["SY0"]
        self.assertListEqual(list1=list(self.recording.get_channel_ids()), list2=expected_channel_ids)

    def test_gains(self):
        expected_gains = np.concatenate([2.34375 * np.ones(shape=384), [1171.875]])
        assert_array_equal(x=self.recording.get_channel_gains(), y=expected_gains)

    def test_offsets(self):
        expected_offsets = np.zeros(shape=385)
        assert_array_equal(x=self.recording.get_channel_offsets(), y=expected_offsets)

    def test_probe_representation(self):
        expected_exception = ValueError
        expected_error_message = "There is no Probe attached to this recording. Use set_probe(...) to attach one."
        with self.assertRaisesRegex(
            expected_exception=expected_exception,
            expected_regex=f"^{escape(expected_error_message)}$",
        ):
            self.recording.get_probe()

    def test_property_keys(self):
        expected_property_keys = [
            "gain_to_uV",
            "offset_to_uV",
            "shank",
            "shank_row",
            "shank_col",
            "good_channel",
            "inter_sample_shift",
            "adc",
            "index_on_probe",
        ]
        self.assertCountEqual(first=self.recording.get_property_keys(), second=expected_property_keys)

    def test_trace_shape(self):
        expected_shape = (21, 385)
        self.assertTupleEqual(tuple1=self.small_scaled_trace.shape, tuple2=expected_shape)

    def test_scaled_trace_dtype(self):
        expected_dtype = np.dtype("float32")
        assert self.small_scaled_trace.dtype == expected_dtype

    def test_unscaled_trace_dtype(self):
        expected_dtype = np.dtype("int16")
        assert self.small_unscaled_trace.dtype == expected_dtype


class TestIblSortingExtractor(TestCase):
    def test_ibl_sorting_extractor(self):
        """
        Here we generate spike train with 3 clusters in a very basic ALF format\
        and read it with the spikeinterface extractor
        """
        sorting = generate_sorting(3, durations=[1000])
        spikes = sorting.to_spike_vector()
        spikes = {"samples": spikes["sample_index"], "clusters": spikes["unit_index"]}
        clusters = {"amps": np.ones(3) * 50 / 1e6}
        one = IblRecordingExtractor._get_default_one()
        with mock.patch("brainbox.io.one.SpikeSortingLoader.load_spike_sorting", side_effect=((spikes, clusters, {}),)):
            sorting = read_ibl_sorting(pid=PID, one=one)
        self.assertEqual(sorting.to_spike_vector()["sample_index"].size, spikes["samples"].size)


if __name__ == "__main__":
    TestDefaultIblStreamingRecordingExtractorApBand.setUpClass()
    test1 = TestDefaultIblStreamingExtractorApBand()
    test1.setUp()
    test1.test_get_stream_names()
    test1.test_dtype()
    test1.test_channel_ids()
    test1.test_gains()
    test1.test_offsets()
    test1.test_int16_gain_to_uV()
    test1.test_probe_representation()
    test1.test_property_keys()
    test1.test_trace_shape()
    test1.test_scaled_trace_dtype()
    test1.test_unscaled_trace_dtype()

    TestIblStreamingRecordingExtractorApBandWithLoadSyncChannel.setUpClass()
    test2 = TestIblStreamingExtractorApBandWithLoadSyncChannel()
    test2.setUp()
    test2.test_get_stream_names()
    test2.test_get_stream_names()
    test2.test_dtype()
    test2.test_channel_ids()
    test2.test_gains()
    test2.test_offsets()
    test2.test_int16_gain_to_uV()
    test2.test_probe_representation()
    test2.test_property_keys()
    test2.test_trace_shape()
    test2.test_scaled_trace_dtype()
    test2.test_unscaled_trace_dtype()
