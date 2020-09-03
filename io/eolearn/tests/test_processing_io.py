""" Testing SentinelHubInputTask
"""
import os
import shutil
import unittest
from concurrent import futures
import datetime as dt

import numpy as np
from sentinelhub import CRS, BBox, DataSource
from eolearn.io import SentinelHubInputTask, SentinelHubDemTask
from eolearn.core import FeatureType, EOPatch

from test_io import IoTestCase


def array_stats(array):
    time, height, width, _ = array.shape
    edge1 = np.mean(array[int(time/2):, 0, 0, :])
    edge2 = np.mean(array[:max(int(time/2), 1), -1, -1, :])
    edge3 = np.mean(array[:, int(height/2), int(width/2), :])

    stats = np.round(np.array([edge1, edge2, edge3]), 4)

    return stats


class TestProcessingIO(unittest.TestCase):
    """ Test cases for SentinelHubInputTask
    """
    size = (99, 101)
    bbox = BBox(bbox=[268892, 4624365, 268892+size[0]*10, 4624365+size[1]*10], crs=CRS.UTM_33N)
    time_interval = ('2017-12-15', '2017-12-30')
    maxcc = 0.8
    time_difference = dt.timedelta(minutes=60)
    max_threads = 3

    def test_S2L1C_float32_uint16(self):
        """ Download S2L1C bands and dataMask
        """
        test_dir = os.path.dirname(os.path.realpath(__file__))
        cache_folder = os.path.join(test_dir, 'cache_test')

        if os.path.exists(cache_folder):
            shutil.rmtree(cache_folder)

        task = SentinelHubInputTask(
            bands_feature=(FeatureType.DATA, 'BANDS'),
            additional_data=[(FeatureType.MASK, 'dataMask')],
            size=self.size,
            maxcc=self.maxcc,
            time_difference=self.time_difference,
            data_source=DataSource.SENTINEL2_L1C,
            max_threads=self.max_threads,
            cache_folder=cache_folder
        )

        eopatch = task.execute(bbox=self.bbox, time_interval=self.time_interval)
        bands = eopatch[(FeatureType.DATA, 'BANDS')]
        is_data = eopatch[(FeatureType.MASK, 'dataMask')]

        self.assertTrue(np.allclose(array_stats(bands), [0.0233, 0.0468, 0.0252]))

        width, height = self.size
        self.assertTrue(bands.shape == (4, height, width, 13))
        self.assertTrue(is_data.shape == (4, height, width, 1))
        self.assertTrue(len(eopatch.timestamp) == 4)
        self.assertTrue(bands.dtype == np.float32)

        self.assertTrue(os.path.exists(cache_folder))

        # change task's bans_dtype and run it again
        task.bands_dtype = np.uint16

        eopatch = task.execute(bbox=self.bbox, time_interval=self.time_interval)
        bands = eopatch[(FeatureType.DATA, 'BANDS')]

        self.assertTrue(np.allclose(array_stats(bands), [232.5769, 467.5385, 251.8654]))

        self.assertTrue(bands.dtype == np.uint16)

        shutil.rmtree(cache_folder)

    def test_specific_bands(self):
        """ Download S2L1C bands and dataMask
        """
        task = SentinelHubInputTask(
            bands_feature=(FeatureType.DATA, 'BANDS'),
            bands=["B01", "B02", "B03"],
            additional_data=[(FeatureType.MASK, 'dataMask')],
            size=self.size,
            maxcc=self.maxcc,
            time_difference=self.time_difference,
            data_source=DataSource.SENTINEL2_L1C,
            max_threads=self.max_threads
        )

        eopatch = task.execute(bbox=self.bbox, time_interval=self.time_interval)
        bands = eopatch[(FeatureType.DATA, 'BANDS')]

        self.assertTrue(np.allclose(array_stats(bands), [0.0648, 0.1193, 0.063]))

        width, height = self.size
        self.assertTrue(bands.shape == (4, height, width, 3))

    def test_scl_only(self):
        """ Download just SCL, without any other bands
        """
        task = SentinelHubInputTask(
            bands_feature=None,
            additional_data=[(FeatureType.DATA, 'SCL')],
            size=self.size,
            maxcc=self.maxcc,
            time_difference=self.time_difference,
            data_source=DataSource.SENTINEL2_L2A,
            max_threads=self.max_threads
        )

        eopatch = task.execute(bbox=self.bbox, time_interval=self.time_interval)
        scl = eopatch[(FeatureType.DATA, 'SCL')]

        width, height = self.size
        self.assertTrue(scl.shape == (4, height, width, 1))

    def test_single_scene(self):
        """ Download S2L1C bands and dataMask
        """
        task = SentinelHubInputTask(
            bands_feature=(FeatureType.DATA, 'BANDS'),
            additional_data=[(FeatureType.MASK, 'dataMask')],
            size=self.size,
            maxcc=self.maxcc,
            time_difference=self.time_difference,
            data_source=DataSource.SENTINEL2_L1C,
            max_threads=self.max_threads,
            single_scene=True,
            mosaicking_order="leastCC"
        )

        eopatch = task.execute(bbox=self.bbox, time_interval=self.time_interval)
        bands = eopatch[(FeatureType.DATA, 'BANDS')]
        is_data = eopatch[(FeatureType.MASK, 'dataMask')]

        width, height = self.size
        self.assertTrue(bands.shape == (1, height, width, 13))
        self.assertTrue(is_data.shape == (1, height, width, 1))
        self.assertTrue(len(eopatch.timestamp) == 1)

    def test_additional_data(self):
        """ Download additional data, such as viewAzimuthMean, sunAzimuthAngles...
        """
        task = SentinelHubInputTask(
            bands_feature=(FeatureType.DATA, 'BANDS'),
            bands=['B01', 'B02', 'B05'],
            additional_data=[
                (FeatureType.MASK, 'dataMask', 'IS_DATA'),
                (FeatureType.MASK, 'CLM'),
                (FeatureType.MASK, 'SCL'),
                (FeatureType.MASK, 'SNW'),
                (FeatureType.MASK, 'CLD'),
                (FeatureType.DATA, 'CLP'),
                (FeatureType.DATA, 'viewAzimuthMean', 'view_azimuth_mean'),
                (FeatureType.DATA, 'sunAzimuthAngles'),
                (FeatureType.DATA, 'sunZenithAngles')
            ],
            size=self.size,
            maxcc=self.maxcc,
            time_difference=self.time_difference,
            data_source=DataSource.SENTINEL2_L2A,
            max_threads=self.max_threads
        )

        eopatch = task.execute(bbox=self.bbox, time_interval=self.time_interval)

        bands = eopatch[(FeatureType.DATA, 'BANDS')]
        is_data = eopatch[(FeatureType.MASK, 'IS_DATA')]
        clm = eopatch[(FeatureType.MASK, 'CLM')]
        scl = eopatch[(FeatureType.MASK, 'SCL')]
        snw = eopatch[(FeatureType.MASK, 'SNW')]
        cld = eopatch[(FeatureType.MASK, 'CLD')]
        clp = eopatch[(FeatureType.DATA, 'CLP')]
        view_azimuth_mean = eopatch[(FeatureType.DATA, 'view_azimuth_mean')]
        sun_azimuth_angles = eopatch[(FeatureType.DATA, 'sunAzimuthAngles')]
        sun_zenith_angles = eopatch[(FeatureType.DATA, 'sunZenithAngles')]

        self.assertTrue(np.allclose(array_stats(bands), [0.027,  0.0243, 0.0162]))

        width, height = self.size
        self.assertTrue(bands.shape == (4, height, width, 3))
        self.assertTrue(is_data.shape == (4, height, width, 1))
        self.assertTrue(is_data.dtype == np.bool)
        self.assertTrue(clm.shape == (4, height, width, 1))
        self.assertTrue(clm.dtype == np.uint8)
        self.assertTrue(scl.shape == (4, height, width, 1))
        self.assertTrue(snw.shape == (4, height, width, 1))
        self.assertTrue(cld.shape == (4, height, width, 1))
        self.assertTrue(clp.shape == (4, height, width, 1))
        self.assertTrue(view_azimuth_mean.shape == (4, height, width, 1))
        self.assertTrue(sun_azimuth_angles.shape == (4, height, width, 1))
        self.assertTrue(sun_zenith_angles.shape == (4, height, width, 1))
        self.assertTrue(len(eopatch.timestamp) == 4)

    def test_aux_request_args(self):
        """ Download low resolution data with `PREVIEW` mode
        """
        task = SentinelHubInputTask(
            bands_feature=(FeatureType.DATA, 'BANDS'),
            resolution=260,
            maxcc=self.maxcc,
            time_difference=self.time_difference,
            data_source=DataSource.SENTINEL2_L1C,
            max_threads=self.max_threads,
            aux_request_args={'dataFilter': {'previewMode': 'PREVIEW'}}
        )

        eopatch = task.execute(bbox=self.bbox, time_interval=self.time_interval)
        bands = eopatch[(FeatureType.DATA, 'BANDS')]

        self.assertTrue(bands.shape == (4, 4, 4, 13))
        self.assertTrue(np.allclose(array_stats(bands), [0.0, 0.0493, 0.0277]))

    def test_dem(self):
        task = SentinelHubDemTask(
            resolution=10,
            dem_feature=(FeatureType.DATA_TIMELESS, 'DEM'),
            max_threads=3
        )

        eopatch = task.execute(bbox=self.bbox)

        dem = eopatch.data_timeless['DEM']

        width, height = self.size
        self.assertTrue(dem.shape == (height, width, 1))

    def test_dem_wrong_feature(self):
        with self.assertRaises(ValueError, msg='Expected a ValueError when providing a wrong feature.'):
            SentinelHubDemTask(resolution=10, dem_feature=(FeatureType.DATA, 'DEM'), max_threads=3)

    def test_multi_processing(self):
        task = SentinelHubInputTask(
            bands_feature=(FeatureType.DATA, 'BANDS'),
            bands=["B01", "B02", "B03"],
            additional_data=[(FeatureType.MASK, 'dataMask')],
            size=self.size,
            maxcc=self.maxcc,
            time_difference=self.time_difference,
            data_source=DataSource.SENTINEL2_L1C,
            max_threads=self.max_threads
        )

        time_intervals = [
            ('2017-01-01', '2017-01-30'),
            ('2017-02-01', '2017-02-28'),
            ('2017-03-01', '2017-03-30'),
            ('2017-04-01', '2017-04-30'),
            ('2017-05-01', '2017-05-30'),
            ('2017-06-01', '2017-06-30')
        ]

        with futures.ProcessPoolExecutor(max_workers=3) as executor:
            tasks = [executor.submit(task.execute, None, self.bbox, interval) for interval in time_intervals]
            eopatches = [task.result() for task in futures.as_completed(tasks)]

        array = np.concatenate([eop.data['BANDS'] for eop in eopatches], axis=0)

        width, height = self.size
        self.assertTrue(array.shape == (20, height, width, 3))


class TestSentinelHubInputTaskDataSources(unittest.TestCase):
    """ Integration tests for all supported data sources
    """
    @classmethod
    def setUpClass(cls):
        bbox = BBox(bbox=(-5.05, 48.0, -5.00, 48.05), crs=CRS.WGS84)
        bbox2 = BBox(bbox=(-72.2, -70.4, -71.6, -70.2), crs=CRS.WGS84)
        cls.size = (50, 40)
        time_interval = ('2020-06-1', '2020-06-10')
        time_difference = dt.timedelta(minutes=60)
        cls.data_feature = FeatureType.DATA, 'BANDS'
        cls.mask_feature = FeatureType.MASK, 'dataMask'

        s3slstr_500m = DataSource.SENTINEL3_SLSTR.define_from(
            'SENTINEL3_SLSTR_500m',
            bands=('S2', 'S3', 'S6')
        )
        s5p_co = DataSource.SENTINEL5P.define_from(
            'SENTINEL5P_CO',
            bands=('CO',)
        )

        cls.test_cases = [
            IoTestCase(
                name='Sentinel-2 L2A',
                request=SentinelHubInputTask(
                    bands_feature=cls.data_feature,
                    additional_data=[cls.mask_feature],
                    size=cls.size,
                    time_difference=time_difference,
                    data_source=DataSource.SENTINEL2_L2A
                ),
                bbox=bbox,
                time_interval=time_interval,
                data_size=12,
                timestamp_length=2,
                stats=[0.4681, 0.6334, 0.7608]
            ),
            IoTestCase(
                name='Landsat8',
                request=SentinelHubInputTask(
                    bands_feature=cls.data_feature,
                    additional_data=[cls.mask_feature],
                    size=cls.size,
                    time_difference=time_difference,
                    data_source=DataSource.LANDSAT8
                ),
                bbox=bbox,
                time_interval=time_interval,
                data_size=11,
                timestamp_length=1,
                stats=[0.2206, 0.2684, 0.198]
            ),
            IoTestCase(
                name='MODIS',
                request=SentinelHubInputTask(
                    bands_feature=cls.data_feature,
                    additional_data=[cls.mask_feature],
                    size=cls.size,
                    time_difference=time_difference,
                    data_source=DataSource.MODIS
                ),
                bbox=bbox,
                time_interval=time_interval,
                data_size=7,
                timestamp_length=10,
                stats=[0.0073, 0.0101, 0.1448]
            ),
            IoTestCase(
                name='MODIS',
                request=SentinelHubInputTask(
                    bands_feature=cls.data_feature,
                    additional_data=[cls.mask_feature],
                    size=cls.size,
                    time_difference=time_difference,
                    data_source=DataSource.MODIS
                ),
                bbox=bbox,
                time_interval=time_interval,
                data_size=7,
                timestamp_length=10,
                stats=[0.0073, 0.0101, 0.1448]
            ),
            IoTestCase(
                name='Sentinel-1 IW',
                request=SentinelHubInputTask(
                    bands_feature=cls.data_feature,
                    additional_data=[cls.mask_feature],
                    size=cls.size,
                    time_difference=time_difference,
                    data_source=DataSource.SENTINEL1_IW
                ),
                bbox=bbox,
                time_interval=time_interval,
                data_size=2,
                timestamp_length=5,
                stats=[0.0168, 0.0032, 0.0094]
            ),
            IoTestCase(
                name='Sentinel-1 IW ASCENDING',
                request=SentinelHubInputTask(
                    bands_feature=cls.data_feature,
                    additional_data=[cls.mask_feature],
                    size=cls.size,
                    time_difference=time_difference,
                    data_source=DataSource.SENTINEL1_IW_ASC
                ),
                bbox=bbox,
                time_interval=time_interval,
                data_size=2,
                timestamp_length=1,
                stats=[0.0428, 0.0199, 0.0235]
            ),
            IoTestCase(
                name='Sentinel-1 EW DESCENDING',
                request=SentinelHubInputTask(
                    bands_feature=cls.data_feature,
                    additional_data=[cls.mask_feature],
                    size=cls.size,
                    time_difference=time_difference,
                    data_source=DataSource.SENTINEL1_EW_DES
                ),
                bbox=bbox2,
                time_interval=time_interval,
                data_size=2,
                timestamp_length=1,
                stats=[np.nan, 0.2195, 0.4114]
            ),
            IoTestCase(
                name='Sentinel-1 EW DESCENDING',
                request=SentinelHubInputTask(
                    bands_feature=cls.data_feature,
                    additional_data=[cls.mask_feature],
                    size=cls.size,
                    time_difference=time_difference,
                    data_source=DataSource.SENTINEL1_EW_DES
                ),
                bbox=bbox2,
                time_interval=time_interval,
                data_size=2,
                timestamp_length=1,
                stats=[np.nan, 0.2195, 0.4114]
            ),
            IoTestCase(
                name='Sentinel-3 OLCI',
                request=SentinelHubInputTask(
                    bands_feature=cls.data_feature,
                    additional_data=[cls.mask_feature],
                    size=cls.size,
                    time_difference=time_difference,
                    data_source=DataSource.SENTINEL3_OLCI
                ),
                bbox=bbox,
                time_interval=time_interval,
                data_size=21,
                timestamp_length=11,
                stats=[0.2064, 0.1354, 0.1905]
            ),
            IoTestCase(
                name='Sentinel-3 SLSTR 500m resolution',
                request=SentinelHubInputTask(
                    bands_feature=cls.data_feature,
                    additional_data=[cls.mask_feature],
                    size=cls.size,
                    time_difference=time_difference,
                    data_source=s3slstr_500m
                ),
                bbox=bbox,
                time_interval=time_interval,
                data_size=3,
                timestamp_length=23,
                stats=[np.nan, 0.1049, np.nan]
            ),
            IoTestCase(
                name='Sentinel-5P',
                request=SentinelHubInputTask(
                    bands_feature=cls.data_feature,
                    additional_data=[cls.mask_feature],
                    size=cls.size,
                    time_difference=time_difference,
                    data_source=s5p_co
                ),
                bbox=bbox,
                time_interval=('2020-06-1', '2020-06-1'),
                data_size=1,
                timestamp_length=1,
                stats=[0.0351, 0.034,  0.0351]
            ),
        ]

    def test_return_type(self):
        for test in self.test_cases:
            with self.subTest(msg='Test case {}'.format(test.name)):
                self.assertTrue(isinstance(test.eop, EOPatch), 'Expected return type is EOPatch')

    def test_dimensions(self):
        width, height = self.size
        for test in self.test_cases:
            with self.subTest(msg='Test case {}'.format(test.name)):
                data = test.eop[self.data_feature]
                self.assertEqual(data.shape, (test.timestamp_length, height, width, test.data_size))

                timestamps = test.eop.timestamp
                self.assertEqual(len(timestamps), test.timestamp_length)

    def test_stats(self):
        for test in self.test_cases:
            with self.subTest(msg='Test case {}'.format(test.name)):
                data = test.eop[self.data_feature]
                stats = array_stats(data)
                self.assertTrue(np.allclose(stats, test.stats, equal_nan=True),
                                f'Expected stats: {test.stats}, got {stats}')


if __name__ == '__main__':
    unittest.main()
