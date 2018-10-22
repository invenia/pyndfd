# Copyright (c) 2015 Marty Sullivan
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
NDFD Forecast Retrieval Routines

Author:  Marty J. Sullivan
Purpose: Routines that will cache NDFD forecast variables locally
            to allow for easy and fast forecast analysis by lat/lon

"""

###########
#         #
# IMPORTS #
#         #
###########
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
from getpass import getuser
from math import isnan, sqrt
from os import makedirs, path
from shutil import rmtree
from sys import stderr
from tempfile import gettempdir

import pygrib
import six.moves.urllib.request as request
from ncepgrib2 import Grib2Decode
from numpy.ma.core import MaskedConstant as NaN
from pyproj import Geod, Proj
from six import iterbytes

from pyndfd.ndfd_defs import ndfd_defs
from pyndfd.utils import deprecate_func

#############
#           #
# CONSTANTS #
#           #
#############

DEFS = ndfd_defs()
G = Geod(ellps="clrk66")

CACHE_SERVER_BUFFER_MIN = 20

NDFD_LOCAL_SERVER = None
NDFD_LOCAL_SERVER_IS_DIR = False
NDFD_REMOTE_SERVER = "http://tgftp.nws.noaa.gov/SL.us008001/ST.opnl/DF.gr2/"
NDFD_DIR = "DC.ndfd" + path.sep + "AR.{0}" + path.sep + "VP.{1}" + path.sep
NDFD_STATIC = "static" + path.sep + "DC.ndfd" + path.sep + "AR.{0}" + path.sep
NDFD_VAR = "ds.{0}.bin"
NDFD_TMP = gettempdir() + path.sep + str(getuser()) + "_pyndfd" + path.sep

########################
#                      #
# FUNCTION DEFINITIONS #
#                      #
########################


def set_local_cache_server(uri, is_local_dir=False):
    """
    Set a server to use instead of weather.noaa.gov

    Args:
        uri (str): String denoting the server URI to use
        is_local_dir (bool): Boolean denoting if the local cache server is a local
                       file system directory
    """
    global NDFD_LOCAL_SERVER
    NDFD_LOCAL_SERVER = uri

    global NDFD_LOCAL_SERVER_IS_DIR
    NDFD_LOCAL_SERVER_IS_DIR = is_local_dir


def set_tmp_folder(path):
    """
    Change the temporary folder path

    Args:
        path (str): String denoting the tmp folder path
    """
    global NDFD_TMP
    NDFD_TMP = path


def std_dev(vals):
    """
    Calculate the standard deviation of a list of float values

    Args:
        vals ([float]): List of float values to use in calculation

    Returns:
        float: The standard deviation
    """
    mean = sum(vals) / len(vals)
    squared = []
    for val in vals:
        squared.append(pow(val - mean, 2) * 1.0)
    variance = sum(squared) / len(squared)
    return sqrt(variance)


def median(vals):
    """
    Calculate the median of a list of int/float values

    Args:
        vals ([int/float]): List of int/float values to use in calculation

    Returns:
        int: The median value
    """
    sorted_list = sorted(vals)
    list_length = len(vals)
    index = (list_length - 1) // 2
    if list_length % 2:
        return sorted_list[index]
    else:
        return (sorted_list[index] + sorted_list[index + 1]) / 2.0


def get_latest_forecast_time():
    """
    For caching purposes, compare this time to cached time to see if
    the cached variable needs to be updated

    Args:
        None

    Returns:
        datetime: The latest forecast time
    """
    latest_time = datetime.datetime.utcnow()
    if latest_time.minute <= CACHE_SERVER_BUFFER_MIN:
        latest_time = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    return latest_time.replace(minute=0, second=0, microsecond=0)


def get_variable(var, area):
    """
    Cache the requested variable if not already cached and return the paths
    of the cached files

    Args:
        var (str): The NDFD variable to retrieve
        area (str): The NDFD grid area to retrieve

    Returns:
        list: A list of paths to the cached files
    """

    gribs = []
    dir_time = NDFD_TMP + get_latest_forecast_time().strftime("%Y-%m-%d-%H") + path.sep
    if not path.isdir(dir_time):
        try:
            rmtree(NDFD_TMP)
        except Exception:
            pass
        makedirs(dir_time)
    if area in DEFS["vars"]:
        for vp in DEFS["vars"][area]:
            if var in DEFS["vars"][area][vp]:
                var_dir = NDFD_DIR.format(area, vp)
                var_name = var_dir + NDFD_VAR.format(var)
                local_dir = dir_time + var_dir
                local_var = dir_time + var_name
                if not path.isdir(local_dir):
                    makedirs(local_dir)
                if not path.isfile(local_var):
                    if NDFD_LOCAL_SERVER is not None:
                        prepend = ""
                        if NDFD_LOCAL_SERVER_IS_DIR:
                            prepend = "File:"
                        remote_var = path.join(prepend + NDFD_LOCAL_SERVER, var_name)
                        request.urlretrieve(remote_var, local_var)
                    else:
                        remote_var = NDFD_REMOTE_SERVER + var_name
                        request.urlretrieve(remote_var, local_var)
                if not path.isfile(local_var):
                    raise RuntimeError(
                        "Cannot retrieve NDFD variables at this time. "
                        "Try again in a moment."
                    )
                gribs.append(local_var)
    else:
        raise ValueError("Invalid Area: " + str(area))

    return gribs


def get_elevation_variable(area):
    """
    Cache the static elevation variable if not already cached and return
    the path of the cached file

    Args:
        area (str): The NDFD grid area to retrieve elevation for

    Returns:
        str: The path of the cached file

    Notes:
        - Cannot be retrieved from weather.noaa.gov, must use a local cache server
          using the format in const NDFD_STATIC
        - Puerto Rico terrian info not currently available.
        - Terrain data for NDFD will be updated sometime in 2015
    """

    if area == "puertori":
        raise ValueError(
            "Elevation currently not available for Puerto Rico. Set elev=False"
        )
    if NDFD_LOCAL_SERVER is None:
        raise RuntimeError(
            "Local cache server must provide elevation data. "
            "Specify cache server with ndfd.set_local_cache_server(uri)"
        )
    if not path.isdir(NDFD_TMP):
        makedirs(NDFD_TMP)

    prepend = ""
    if NDFD_LOCAL_SERVER_IS_DIR:
        prepend = "File:"
    remote_var = path.join(
        prepend + NDFD_LOCAL_SERVER, NDFD_STATIC.format(area), NDFD_VAR.format("elev")
    )
    local_dir = NDFD_TMP + NDFD_STATIC.format(area)
    local_var = local_dir + NDFD_VAR.format("elev")
    if not path.isdir(local_dir):
        makedirs(local_dir)
    if not path.isfile(local_var):
        request.urlretrieve(remote_var, local_var)
    if not path.isfile(local_var):
        raise RuntimeError(
            "Cannot retrieve NDFD variables at this time. Try again in a moment."
        )
    return local_var


def get_smallest_grid(lat, lon):
    """
    Use the provided lat, lon coordinates to find the smallest
    NDFD area that contains those coordinates. Return the name of the area.

    Args:
        lat (float): Latitude
        lon (float): Longitude

    Returns:
        str: The name of the smallest area
    """

    smallest = "neast"
    min_dist = G.inv(
        lon, lat, DEFS["grids"][smallest]["lonC"], DEFS["grids"][smallest]["latC"]
    )[-1]

    for area in DEFS["grids"].keys():
        if area == "conus" or area == "nhemi" or area == "npacocn":
            continue
        cur_area = DEFS["grids"][area]
        # NOTE: smallArea is assigned but never used
        # smallArea = DEFS["grids"][smallest]
        dist = G.inv(lon, lat, cur_area["lonC"], cur_area["latC"])[-1]
        if dist < min_dist:
            min_dist = dist
            smallest = area

    return smallest


def get_nearest_grid_point(grb, lat, lon, projparams=None):
    """
    Find the nearest grid point to the provided coordinates in the supplied
    grib message. Return the indexes to the numpy array as well as the
    lat/lon and grid coordinates of the grid point.

    Args:
        grb (str):  The grib message to search
        lat (float):  Latitude
        lon (float):  Longitude
        projparams (dict) [Optional]:  Use to supply different Proj4 parameters
                                       than the supplied grib message uses.

    Returns:
        int: x index into the numpy array
        int: y index into the numpy array
        int: x grid coordinate
        int: y grid coordinate
        float: latitude of the grid point
        float: longitude of the grid point
    """

    if projparams is None:
        p = Proj(grb.projparams)
    else:
        p = Proj(projparams)
    offset_x, offset_y = p(
        grb["longitudeOfFirstGridPointInDegrees"],
        grb["latitudeOfFirstGridPointInDegrees"],
    )
    grid_x, grid_y = p(lon, lat)

    x_name = "DxInMetres"
    y_name = "DyInMetres"
    if not grb.valid_key(x_name) and not grb.valid_key(y_name):
        x_name = "DiInMetres"
        y_name = "DjInMetres"

    x = int(round((grid_x - offset_x) / grb[x_name]))
    y = int(round((grid_y - offset_y) / grb[y_name]))
    g_lon, g_lat = p(
        x * grb[x_name] + offset_x, y * grb[y_name] + offset_y, inverse=True
    )
    return x, y, grid_x, grid_y, g_lat, g_lon


def validate_arguments(var, area, time_step, min_time, max_time):
    """
    Validate the arguments passed into an analysis function to make sure
    they will work with each other.

    Args:
        var (str):  The NDFD variable being requested
        area (str):  The NDFD grid area being requested
        time_step (int): The time step to be used in the returned analysis
        min_time (datetime): The minimum forecast time to analyze
        max_time (datetime): The maximum forecast time to analyze

    Notes:
        - min_time is not currently being evaluated
        - max_time is not currently being evaluated
    """

    if time_step < 1:
        raise ValueError("time_step must be >= 1")

    # if min_time != None and min_time < get_latest_forecast_time():
    #    raise ValueError('min_time is before the current forecast time.')
    # if max_time > ...

    try:
        area_vp = DEFS["vars"][area]
    except KeyError:
        raise ValueError("Invalid Area.")

    valid_var = False
    for vp in area_vp:
        if var in area_vp[vp]:
            valid_var = True
            break
    if not valid_var:
        raise ValueError("Variable not available in area: " + area)


def get_forecast_analysis(
    var, lat, lon, n=0, time_step=1, elev=False, min_time=None, max_time=None, area=None
):
    """
    Analyze a grid point for any NDFD forecast variable in any NDFD grid area.
    The grid point will be the closest point to the supplied coordinates.

    Args:
        var (str):  The NDFD variable to analyzes
        lat (float):  Latitude
        lon (float):  Longitude
        n (int):  The levels away from the grid point to analyze. Default = 0
        time_step (int): The time step in hours to use in analyzing forecasts.
                         Default = 1
        elev (bool):  Boolean that indicates whether to include elevation of the grid
                      points. Default = False
        min_time (datetime): Optional minimum time for the forecast analysis
        max_time (datetime): Optional maximum time for the forecast analysis
        area (str):  Used to specify a specific NDFD grid area. Default is to find the
                     smallest grid the supplied coordinates lie in.

    Returns:
        dict: Forecast Analysis
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    neg_n = n * -1

    if area is None:
        area = get_smallest_grid(lat, lon)
    validate_arguments(var, area, time_step, min_time, max_time)

    analysis = {}
    analysis["var"] = var
    analysis["reqLat"] = lat
    analysis["reqLon"] = lon
    analysis["n"] = n
    analysis["forecastTime"] = get_latest_forecast_time()
    analysis["forecasts"] = {}

    valid_times = []
    for hour in range(0, 250, time_step):
        t = (
            analysis["forecastTime"]
            - datetime.timedelta(hours=analysis["forecastTime"].hour)
            + datetime.timedelta(hours=hour)
        )
        if min_time is not None and t < min_time:
            continue
        if max_time is not None and t > max_time:
            break
        valid_times.append(t)

    var_grbs = get_variable(var, area)
    all_vals = []
    first_run = True
    for g in var_grbs:
        grbs = pygrib.open(g)
        for grb in grbs:
            t = datetime.datetime(
                grb["year"], grb["month"], grb["day"], grb["hour"]
            ) + datetime.timedelta(hours=grb["forecastTime"])
            if t not in valid_times:
                continue

            x, y, grid_x, grid_y, g_lat, g_lon = get_nearest_grid_point(grb, lat, lon)
            if first_run:
                analysis["gridLat"] = g_lat
                analysis["gridLon"] = g_lon
                analysis["units"] = grb["parameterUnits"]

                x_name = "DxInMetres"
                y_name = "DyInMetres"
                if not grb.valid_key(x_name) and not grb.valid_key(y_name):
                    x_name = "DiInMetres"
                    y_name = "DjInMetres"
                analysis["deltaX"] = grb[x_name]
                analysis["deltaY"] = grb[y_name]
                analysis["distance"] = G.inv(lon, lat, g_lon, g_lat)[-1]
                first_run = False

            vals = []
            if elev:
                e_grbs = pygrib.open(get_elevation_variable(area))
                e = e_grbs[1]
                e_x, e_y, e_grid_x, e_grid_y, e_lat, e_lon = get_nearest_grid_point(
                    e, lat, lon, projparams=grb.projparams
                )
                e_vals = []
            try:
                if n == 0:
                    val = grb.values[y][x]
                    if type(val) == NaN:
                        val = float("nan")
                    vals.append(val)
                    all_vals.append(val)
                    nearest_val = val
                    if elev:
                        e_val = e.values[e_y][e_x]
                        if type(e_val) == NaN:
                            e_val = float("nan")
                        e_vals.append(e_val)
                        e_nearest_val = e_val
                else:
                    for i in range(min(n, neg_n), max(n, neg_n) + 1):
                        for j in range(min(n, neg_n), max(n, neg_n) + 1):
                            val = grb.values[y + j][x + i]
                            if type(val) == NaN:
                                val = float("nan")
                            vals.append(val)
                            all_vals.append(val)
                            if i == 0 and j == 0:
                                nearest_val = val
                            if elev:
                                e_val = e.values[e_y + j][e_x + i]
                                if type(e_val) == NaN:
                                    e_val = float("nan")
                                e_vals.append(e_val)
                                if i == 0 and j == 0:
                                    e_nearest_val = e_val
            except IndexError:
                raise ValueError(
                    "Given coordinates go beyond the grid. "
                    "Use different coordinates, a larger area or use a smaller n value."
                )

            forecast = {}
            forecast["nearest"] = nearest_val
            if len(vals) > 1:
                forecast["points"] = len(vals)
                forecast["min"] = min(vals)
                forecast["max"] = max(vals)
                forecast["mean"] = sum(vals) / len(vals)
                forecast["median"] = median(vals)
                forecast["stdDev"] = std_dev(vals)
                forecast["sum"] = sum(vals)

            if elev:
                elevation = {}
                elevation["nearest"] = e_nearest_val
                elevation["units"] = e["parameterUnits"]
                if len(e_vals) > 1:
                    elevation["points"] = len(e_vals)
                    elevation["min"] = min(e_vals)
                    elevation["max"] = max(e_vals)
                    elevation["mean"] = sum(e_vals) / len(e_vals)
                    elevation["median"] = median(e_vals)
                    elevation["stdDev"] = std_dev(e_vals)
                analysis["elevation"] = elevation
                e_grbs.close()
                elev = False

            analysis["forecasts"][t] = forecast
        grbs.close()

    analysis["min"] = float("nan")
    analysis["max"] = float("nan")
    analysis["mean"] = float("nan")
    analysis["median"] = float("nan")
    analysis["stdDev"] = float("nan")
    analysis["sum"] = float("nan")

    if len(all_vals) > 0:
        analysis["min"] = min(all_vals)
        analysis["max"] = max(all_vals)
        analysis["mean"] = sum(all_vals) / len(all_vals)
        analysis["median"] = median(all_vals)
        analysis["stdDev"] = std_dev(all_vals)
        analysis["sum"] = sum(all_vals)

    return analysis


def unpack_string(raw):
    """
    To unpack the packed binary string in the local use section of NDFD gribs

    Args:
        raw (list): The raw byte string containing the packed data

    Returns:
        list: List of codes
    """

    num_bytes, remainder = divmod(len(raw) * 8 - 1, 7)

    i = int("".join(["%.2x" % x for x in iterbytes(raw)]), 16)
    if remainder:
        i >>= remainder

    msg = []
    for _ in range(num_bytes):
        byte = i & 127
        if not byte:
            msg.append(ord("\n"))
        elif 32 <= byte <= 126:
            msg.append(byte)
        i >>= 7
    msg.reverse()
    msg = "".join([chr(c) for c in msg])

    codes = []
    for line in msg.splitlines():
        if len(line) >= 4 and (
            line.count(":") >= 4 or line.count(".") >= 1 or "<None>" in line
        ):
            codes.append(line)

    return codes


def parse_weather_string(wx_string):
    """
    To create a readable, English string describing the weather

    Args:
        wx_string (str): The weather string to translate into English

    Returns:
        str: Weather string
        float: Visibility

    Notes:
        - See http://graphical.weather.gov/docs/grib_design.html for details
    """

    weather_string = ""
    visibility = float("nan")

    words = wx_string.split("^")
    for word in words:
        entries = word.split(":")
        coverage = entries[0]
        weather = entries[1]
        intensity = entries[2]
        vis = entries[3]
        attributes = entries[4].split(",")

        ws = ""
        prepend = False
        _OR = False
        likely = False

        if "<NoCov>" in coverage:
            pass
        elif "Lkly" in coverage:
            likely = True
        elif coverage in DEFS["wx"]["coverage"]:
            ws += DEFS["wx"]["coverage"][coverage] + " "
        else:
            stderr.write("WARNING: Unknown coverage code: " + coverage + "\n")
            stderr.flush()

        if "<NoInten>" in intensity:
            pass
        elif intensity in DEFS["wx"]["intensity"]:
            ws += DEFS["wx"]["intensity"][intensity] + " "
        else:
            stderr.write("WARNING: Unknown intensity code: " + intensity + "\n")
            stderr.flush()

        if "<NoWx>" in weather:
            pass
        elif weather in DEFS["wx"]["weather"]:
            ws += DEFS["wx"]["weather"][weather] + " "
        else:
            stderr.write("WARNING: Unknown weather code: " + weather + "\n")
            stderr.flush()

        if likely:
            ws += "likely "

        for attribute in attributes:
            if attribute == "" or "<None>" in attribute or "Mention" in attribute:
                continue
            elif attribute == "Primary":
                prepend = True
            elif attribute == "OR":
                _OR = True
            elif attribute in DEFS["wx"]["hazards"]:
                ws += "with " + DEFS["wx"]["hazards"][attribute] + " "
            elif attribute in DEFS["wx"]["attributes"]:
                ws += DEFS["wx"]["attributes"][attribute] + " "
            else:
                stderr.write("WARNING: Unknown attribute code: " + attribute + "\n")
                stderr.flush()

        if len(weather_string) == 0:
            weather_string = ws
        else:
            if prepend and _OR:
                weather_string = ws + "or " + weather_string.lower()
            elif prepend:
                weather_string = ws + "and " + weather_string.lower()
            elif _OR:
                weather_string += "or " + ws.lower()
            else:
                weather_string += "and " + ws.lower()

        if "<NoVis>" in vis:
            vis = float("nan")
        elif vis in DEFS["wx"]["visibility"]:
            vis = DEFS["wx"]["visibility"][vis]
        else:
            stderr.write("WARNING: Unknown visibility code: " + vis + "\n")
            stderr.flush()
            vis = float("nan")

        if not isnan(vis) and isnan(visibility):
            visibility = vis
        elif not isnan(vis) and vis < visibility:
            visibility = vis

    if len(weather_string) == 0:
        weather_string = "<NoWx>"
    else:
        weather_string = weather_string.strip().capitalize()

    return weather_string, visibility


def parse_advisory_string(wwa_string):
    """
    To create a readable, English string describing current weather hazards

    Args:
        wwa_string: The Watch, Warning, Advisory string to translate to English

    Returns:
        str: Advisory string

    Notes:
        - See http://graphical.weather.gov/docs/grib_design.html for details
    """

    advisory_string = ""

    words = wwa_string.split("^")
    for word in words:
        if "<None>" in word:
            continue

        entries = word.split(".")
        hazard = entries[0]
        advisory = entries[1]

        if hazard in DEFS["wwa"]["hazards"]:
            advisory_string += DEFS["wwa"]["hazards"][hazard] + " "
        else:
            stderr.write("WARNING: Unknown hazard code: " + hazard + "\n")
            stderr.flush()

        if advisory in DEFS["wwa"]["advisories"]:
            advisory_string += DEFS["wwa"]["advisories"][advisory] + "\n"
        else:
            stderr.write("WARNING: Unknown advisory code: " + advisory + "\n")
            stderr.flush()

    if len(advisory_string) == 0:
        advisory_string = "<None>"
    else:
        advisory_string = advisory_string.strip().title()

    return advisory_string


def get_weather_analysis(
    lat, lon, time_step=1, min_time=None, max_time=None, area=None
):
    """
    To get an English representation of the current weather and any NWS
    watch, warning, advisories in effect

    Args:
        lat (float): Latitude
        lon (float): Longitude
        time_step (int): The time step in hours to use in anlyzing weather. Default = 1
        min_time (datetime): Optional minimum time for the weather analysis
        max_time (datetime): Optional maximum time for the weather analysis
        area (str): Used to specify a specific NDFD grid area. Default is to find the
                    smallest grid the supplied coordinates lie in.

    Returns:
        dict: Weather analysis
    """

    if area is None:
        area = get_smallest_grid(lat, lon)
    validate_arguments("wx", area, time_step, min_time, max_time)

    analysis = {}
    analysis["reqLat"] = lat
    analysis["reqLon"] = lon
    analysis["forecastTime"] = get_latest_forecast_time()
    analysis["forecasts"] = {}

    valid_times = []
    for hour in range(0, 250, time_step):
        t = (
            analysis["forecastTime"]
            - datetime.timedelta(hours=analysis["forecastTime"].hour)
            + datetime.timedelta(hours=hour)
        )
        if min_time is not None and t < min_time:
            continue
        if max_time is not None and t > max_time:
            break
        valid_times.append(t)

    wx_grbs = get_variable("wx", area)
    first_run = True
    for g in wx_grbs:
        grbs = pygrib.open(g)
        ncepgrbs = Grib2Decode(g)
        for grb in grbs:
            t = datetime.datetime(
                grb["year"], grb["month"], grb["day"], grb["hour"]
            ) + datetime.timedelta(hours=grb["forecastTime"])
            if t not in valid_times:
                continue

            ncepgrb = ncepgrbs[grb.messagenumber - 1]
            if not ncepgrb.has_local_use_section:
                raise RuntimeError(
                    "Unable to read wx definitions from grib. "
                    "Is it not a wx grib file??"
                )

            x, y, grid_x, grid_y, g_lat, g_lon = get_nearest_grid_point(grb, lat, lon)
            if first_run:
                analysis["gridLat"] = g_lat
                analysis["gridLon"] = g_lon

                x_name = "DxInMetres"
                y_name = "DyInMetres"
                if not grb.valid_key(x_name) and not grb.valid_key(y_name):
                    x_name = "DiInMetres"
                    y_name = "DjInMetres"
                analysis["deltaX"] = grb[x_name]
                analysis["deltaY"] = grb[y_name]
                analysis["distance"] = G.inv(lon, lat, g_lon, g_lat)[-1]
                first_run = False

            try:
                val = grb.values[y][x]
            except IndexError:
                raise ValueError("Coordinates outside the given area.")

            forecast = {}
            forecast["wxString"] = None
            forecast["weatherString"] = None
            forecast["visibility"] = float("nan")
            forecast["wwaString"] = None
            forecast["advisoryString"] = None

            if val != grb["missingValue"]:
                defs = unpack_string(ncepgrb._local_use_section)
                forecast["wxString"] = defs[int(val)]
                forecast["weatherString"], forecast[
                    "visibility"
                ] = parse_weather_string(forecast["wxString"])

            analysis["forecasts"][t] = forecast
        grbs.close()

    wwa_grbs = get_variable("wwa", area)
    for g in wwa_grbs:
        grbs = pygrib.open(g)
        ncepgrbs = Grib2Decode(g)
        for grb in grbs:
            t = datetime.datetime(
                grb["year"], grb["month"], grb["day"], grb["hour"]
            ) + datetime.timedelta(hours=grb["forecastTime"])
            if t not in valid_times:
                continue

            ncepgrb = ncepgrbs[grb.messagenumber - 1]
            if not ncepgrb.has_local_use_section:
                raise RuntimeError(
                    "Unable to read wwa definitions from grib. "
                    "Is it not a wwa grib file??"
                )

            x, y, grid_x, grid_y, g_lat, g_lon = get_nearest_grid_point(grb, lat, lon)
            try:
                val = grb.values[y][x]
            except IndexError:
                raise ValueError("Coordinates outside given area.")

            if t not in analysis["forecasts"]:
                forecast = {}
                forecast["wxString"] = None
                forecast["weatherString"] = None
                forecast["visibility"] = float("nan")
                forecast["wwaString"] = None
                forecast["advisoryString"] = None
            else:
                forecast = analysis["forecasts"][t]

            if val != grb["missingValue"]:
                defs = unpack_string(ncepgrb._local_use_section)
                forecast["wwaString"] = defs[int(val)]
                forecast["advisoryString"] = parse_advisory_string(
                    forecast["wwaString"]
                )

            analysis["forecasts"][t] = forecast
        grbs.close()

    return analysis


# TODO: Remove deprecated function names in a future version
setLocalCacheServer = deprecate_func("setLocalCacheServer", set_local_cache_server)
stdDev = deprecate_func("stdDev", std_dev)
getLatestForecastTime = deprecate_func(
    "getLatestForecastTime", get_latest_forecast_time
)
getVariable = deprecate_func("getVariable", get_variable)
getElevationVariable = deprecate_func("getElevationVariable", get_elevation_variable)
getSmallestGrid = deprecate_func("getSmallestGrid", get_smallest_grid)
getNearestGridPoint = deprecate_func("getNearestGridPoint", get_nearest_grid_point)
validateArguments = deprecate_func("validateArguments", validate_arguments)
getForecastAnalysis = deprecate_func("getForecastAnalysis", get_forecast_analysis)
unpackString = deprecate_func("unpackString", unpack_string)
parseWeatherString = deprecate_func("parseWeatherString", parse_weather_string)
parseAdvisoryString = deprecate_func("parseAdvisoryString", parse_advisory_string)
getWeatherAnalysis = deprecate_func("getWeatherAnalysis", get_weather_analysis)
