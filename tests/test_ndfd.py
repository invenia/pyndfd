import datetime
import math
import os.path
import shutil

import pygrib
import six.moves.urllib.request as request

import pytest
from pyndfd import ndfd

FILES_PATH = "./tests/files/local/"
CACHE_PATH = "./tests/files/cache/"


def test_set_local_cache_server():
    uri = "http://local.cache.server"
    ndfd.set_local_cache_server(uri)

    # Need to import the global after changing it to test it
    from pyndfd.ndfd import NDFD_LOCAL_SERVER

    assert NDFD_LOCAL_SERVER == uri

    # Re-set it to None
    ndfd.set_local_cache_server(None)


def test_std_dev():
    data = [1, 2, 3, 4, 5]
    expected = 1.4142135623730951

    # NOTE: This might be a bit risky due to floating point rounding errors
    stddev = ndfd.std_dev(data)
    assert stddev == expected


def test_median():
    data = [1, 2, 3, 4, 5, 6]
    expected = 3.5
    data2 = [1, 2, 3, 4, 5]
    expected2 = 3

    median = ndfd.median(data)
    assert median == expected

    median = ndfd.median(data2)
    assert median == expected2


@pytest.fixture
def mock_utcnow_zero_minute(monkeypatch):
    class MockDatetime(datetime.datetime):
        @classmethod
        def utcnow(cls):
            return datetime.datetime(
                year=2018, month=1, day=1, hour=1, minute=1, second=1, microsecond=1
            )

    monkeypatch.setattr(datetime, "datetime", MockDatetime)


def test_get_latest_forecast_time_before_min(mock_utcnow_zero_minute):
    latest = ndfd.get_latest_forecast_time()
    assert latest.year == 2018
    assert latest.month == 1
    assert latest.day == 1
    assert latest.hour == 0
    assert latest.minute == 0
    assert latest.second == 0
    assert latest.microsecond == 0


@pytest.fixture
def mock_utcnow_thirty_minute(monkeypatch):
    class MockDatetime(datetime.datetime):
        @classmethod
        def utcnow(cls):
            return datetime.datetime(
                year=2018, month=1, day=1, hour=1, minute=30, second=1, microsecond=1
            )

    monkeypatch.setattr(datetime, "datetime", MockDatetime)


def test_get_latest_forecast_time_after_min(mock_utcnow_thirty_minute):
    latest = ndfd.get_latest_forecast_time()
    assert latest.year == 2018
    assert latest.month == 1
    assert latest.day == 1
    assert latest.hour == 1
    assert latest.minute == 0
    assert latest.second == 0
    assert latest.microsecond == 0


def test_get_variable_invalid_area():
    with pytest.raises(ValueError):
        ndfd.get_variable("wrong", "wrong")


@pytest.fixture
def mock_urlretrieve(monkeypatch):
    def mock_retrieve(remote_var, local_var):
        return

    monkeypatch.setattr(request, "urlretrieve", mock_retrieve)


def test_get_variable_no_write(mock_urlretrieve):
    # Set a temp folder and make sure it's empty
    ndfd.set_tmp_folder(FILES_PATH)
    shutil.rmtree(FILES_PATH, ignore_errors=True)

    with pytest.raises(RuntimeError):
        ndfd.get_variable("apt", "conus")


def test_get_variable_no_write_local_set(mock_urlretrieve):
    # Set a temp folder and make sure it's empty
    ndfd.set_tmp_folder(FILES_PATH)
    shutil.rmtree(FILES_PATH, ignore_errors=True)

    ndfd.set_local_cache_server("testserver")
    with pytest.raises(RuntimeError):
        ndfd.get_variable("apt", "conus")


@pytest.fixture
def mock_urlretrieve_write(monkeypatch):
    def mock_retrieve(remote_var, local_var):
        with open(local_var, "w") as f:
            f.write("test")
        return

    monkeypatch.setattr(request, "urlretrieve", mock_retrieve)


def test_get_variable_with_write(mock_urlretrieve_write, mock_utcnow_zero_minute):
    ndfd.set_tmp_folder(FILES_PATH)
    shutil.rmtree(FILES_PATH, ignore_errors=True)
    expected = [
        os.path.join(
            FILES_PATH,
            "2018-01-01-00",
            "DC.ndfd",
            "AR.conus",
            "VP.004-007",
            "ds.apt.bin",
        ),
        os.path.join(
            FILES_PATH,
            "2018-01-01-00",
            "DC.ndfd",
            "AR.conus",
            "VP.001-003",
            "ds.apt.bin",
        ),
    ]

    result = ndfd.get_variable("apt", "conus")
    assert expected[0] in result
    assert expected[1] in result


def test_get_elevation_variable_puertori():
    with pytest.raises(ValueError):
        ndfd.get_elevation_variable("puertori")


def test_get_elevation_variable_no_local_server():
    ndfd.set_local_cache_server(None)
    with pytest.raises(RuntimeError):
        ndfd.get_elevation_variable("hawaii")


def test_get_elevation_variable_fail(mock_urlretrieve):
    ndfd.set_local_cache_server("Test")
    ndfd.set_tmp_folder(FILES_PATH)
    shutil.rmtree(FILES_PATH, ignore_errors=True)

    with pytest.raises(RuntimeError):
        ndfd.get_elevation_variable("hawaii")


def test_get_elevation_variable_pass(mock_urlretrieve_write):
    ndfd.set_local_cache_server("Test")
    ndfd.set_tmp_folder(FILES_PATH)
    shutil.rmtree(FILES_PATH, ignore_errors=True)
    expected = os.path.join(FILES_PATH, "static", "DC.ndfd", "AR.hawaii", "ds.elev.bin")

    result = ndfd.get_elevation_variable("hawaii")
    assert result == expected


def test_get_smallest_grid():
    smallest = ndfd.get_smallest_grid(19.8968, 155.5828)
    assert smallest == "guam"


def test_get_nearest_grid_point():
    ndfd.set_local_cache_server(os.path.abspath(CACHE_PATH))
    ndfd.set_tmp_folder(FILES_PATH)
    shutil.rmtree(FILES_PATH, ignore_errors=True)

    lat = 13.4443
    lon = 144.7937
    var = ndfd.get_variable("apt", "guam")
    grb = pygrib.open(var[0])
    g = grb[1]

    x, y, gx, gy, lat, lon = ndfd.get_nearest_grid_point(g, lat, lon)
    assert x == 46
    assert y == 47
    assert gx == -124300.83910231407
    assert gy == 1417898.070274652
    assert lat == 13.44597837639491
    assert lon == 144.78709722379895


def test_get_nearest_grid_point_projparams():
    ndfd.set_local_cache_server(os.path.abspath(CACHE_PATH))
    ndfd.set_tmp_folder(FILES_PATH)
    shutil.rmtree(FILES_PATH, ignore_errors=True)

    lat = 64.2008
    lon = 133.8202
    var = ndfd.get_variable("tmpblw14d", "alaska")
    grb = pygrib.open(var[0])
    g = grb[1]

    x, y, gx, gy, lat, lon = ndfd.get_nearest_grid_point(
        g, lat, lon, projparams=grb[1].projparams
    )
    assert x == -8
    assert y == 1397
    assert gx == -2643990.9661676404
    assert gy == -650414.9493773177
    assert lat == 64.20485934945911
    assert lon == 133.85279035277563


def test_validate_arguments_bad_timestep():
    with pytest.raises(ValueError):
        ndfd.validate_arguments(None, None, 0, None, None)


def test_validate_arguments_bad_area():
    with pytest.raises(ValueError):
        ndfd.validate_arguments(None, "BadArea", 1, None, None)


def test_validate_arguments_bad_var():
    with pytest.raises(ValueError):
        ndfd.validate_arguments("BadVar", "guam", 1, None, None)


def test_validate_arguments_pass():
    ndfd.validate_arguments("apt", "guam", 1, None, None)


def test_get_forecast_analysis_bad_n_value():
    with pytest.raises(ValueError):
        ndfd.get_forecast_analysis(None, None, None, -1, None, None, None, None, None)


def test_get_forecast_analysis_n_0():
    ndfd.set_local_cache_server(os.path.abspath(CACHE_PATH))
    ndfd.set_tmp_folder(FILES_PATH)
    shutil.rmtree(FILES_PATH, ignore_errors=True)

    lat = 13.4443
    lon = 144.7937
    result = ndfd.get_forecast_analysis(
        "apt",
        lat,
        lon,
        min_time=datetime.datetime.utcnow(),
        max_time=datetime.datetime.utcnow() + datetime.timedelta(days=2),
        elev=True,
    )

    # Test a few variables in the result
    assert result["deltaX"] == 2500.0
    assert result["deltaY"] == 2500.0
    assert result["distance"] == 738.7266092794616
    assert result["min"] == 301.5
    assert result["mean"] == 306.3000011444092


def test_get_forecast_analysis_n_2():
    ndfd.set_local_cache_server(os.path.abspath(CACHE_PATH))
    ndfd.set_tmp_folder(FILES_PATH)
    shutil.rmtree(FILES_PATH, ignore_errors=True)

    lat = 13.4443
    lon = 144.7937
    result = ndfd.get_forecast_analysis(
        "apt",
        lat,
        lon,
        min_time=datetime.datetime.utcnow(),
        max_time=datetime.datetime.utcnow() + datetime.timedelta(days=2),
        elev=True,
        n=2,
    )

    # Test a few variables in the result
    assert result["deltaX"] == 2500.0
    assert result["deltaY"] == 2500.0
    assert result["distance"] == 738.7266092794616
    assert result["min"] == 301.5
    assert result["mean"] == 306.59450065612793


def test_get_forecast_analysis_bad_coordinates():
    ndfd.set_local_cache_server(os.path.abspath(CACHE_PATH))
    ndfd.set_tmp_folder(FILES_PATH)
    shutil.rmtree(FILES_PATH, ignore_errors=True)

    lat = 64.2008
    lon = 133.8202
    with pytest.raises(ValueError):
        ndfd.get_forecast_analysis("tmpblw14d", lat, lon)


def test_unpack_string():
    data = (
        b"\x01\x00\x01\x00\x00\x00\x16\x00\x00\x00\x00\x00\x00\x07\x01"
        b'y;~\xec\xaf\x80G\x98\xba\x08\np\xd7Y\x01"\xd2\xe8 \x00'
    )
    expected = ["<None>", "GL.A", "SC.Y", "HZ.A"]
    result = ndfd.unpack_string(data)

    assert result == expected


WEATHER_STRINGS = [
    ("Lkly:A:-:0SM:LgA", ("Light hail likely with large hail", 0.0)),
    ("Sct:SW:-:<NoVis>:", ("Scattered light snow showers", float("nan"))),
    (
        "Ocnl:R:-:<NoVis>:^Ocnl:S:-:<NoVis>:^SChc:ZR:-:<NoVis>:",
        (
            (
                "Occasional light rain and occasional light snow and slight chance of "
                "light freezing rain"
            ),
            float("nan"),
        ),
    ),
    (
        "Wide:FR:-:<NoVis>:OLA",
        ("Widespread light frost on outlying areas", float("nan")),
    ),
    ("<NoCov>:<NoWx>:<NoInten>:<NoVis>:", ("<NoWx>", float("nan"))),
    (
        "Sct:RW:-:<NoVis>:^Iso:T:m:<NoVis>:",
        (
            "Scattered light rain showers and isolated moderate thunderstorms",
            float("nan"),
        ),
    ),
    (
        "Sct:T:+:<NoVis>:DmgW,LgA",
        (
            "Scattered heavy thunderstorms with damaging winds with large hail",
            float("nan"),
        ),
    ),
    ("Wrong:Wrong:Wrong:Wrong:Wrong,Primary,OR,Mention", ("<NoWx>", float("nan"))),
    (
        "Lkly:A:-:<NoVis>:^Lkly:A:-:0SM:LgA,Primary,OR",
        ("Light hail likely with large hail or light hail likely", 0.0),
    ),
    (
        "Lkly:A:-:<NoVis>:^Lkly:A:-:0SM:Primary",
        ("Light hail likely and light hail likely", 0.0),
    ),
    ("Lkly:A:-:1SM:^Lkly:A:-:0SM:OR", ("Light hail likely or light hail likely", 0.0)),
]


@pytest.mark.parametrize(
    "weather_string", WEATHER_STRINGS, ids=[x[0] for x in WEATHER_STRINGS]
)
def test_parse_weather_string(weather_string):
    wx_str = weather_string[0]
    expected = weather_string[1]
    result = ndfd.parse_weather_string(wx_str)

    assert result[0] == expected[0]
    r_v = result[1]
    if math.isnan(r_v):
        assert math.isnan(expected[1])
    else:
        assert r_v == expected[1]


ADVISORY_STRINGS = [
    ("AF.W", "Ash Fall Warning"),
    ("XX.X", "<None>"),
    ("<None>", "<None>"),
]


@pytest.mark.parametrize(
    "advisory_string", ADVISORY_STRINGS, ids=[x[0] for x in ADVISORY_STRINGS]
)
def test_parse_advisory_string(advisory_string):
    wwa_string = advisory_string[0]
    expected = advisory_string[1]
    result = ndfd.parse_advisory_string(wwa_string)

    assert result == expected


def test_get_weather_analysis():
    ndfd.set_local_cache_server(os.path.abspath(CACHE_PATH))
    ndfd.set_tmp_folder(FILES_PATH)
    shutil.rmtree(FILES_PATH, ignore_errors=True)

    lat = 13.4443
    lon = 144.7937
    result = ndfd.get_weather_analysis(
        lat,
        lon,
        min_time=datetime.datetime.utcnow(),
        max_time=datetime.datetime.utcnow() + datetime.timedelta(days=2),
    )

    # Test a few variables in the result
    assert result["deltaX"] == 2500.0
    assert result["deltaY"] == 2500.0
    assert result["distance"] == 738.6436300839714
    assert result["reqLat"] == lat
    assert result["reqLon"] == lon
