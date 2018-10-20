from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime, timedelta
from time import time

from pyndfd import ndfd


def k_to_f(k):
    return "{0:.2f}F".format((k - 273.15) * 1.8 + 32.0)


def mm_to_in(mm):
    return '{0:.2f}"'.format(mm * 0.03937)


def m_to_ft(m):
    return "{0:.2f}'".format(m * 3.2808)


def m_to_in(m):
    return '{0:.2f}"'.format(m * 39.370)


def percent(pc):
    return str(pc) + "%"


# It's important to set the cache server to our own, or vars will be retrieved from NWS
# (slow)
ndfd.set_local_cache_server("http://ndfd.eas.cornell.edu/")

# game farm rd
lat = 42.449167
lon = -76.449034

# variable to get
var = "temp"

# time step for forecasts
time_step = 3

# the minimum time and maximum time you would like to get back
minTime = datetime.utcnow() + timedelta(hours=0)
maxTime = datetime.utcnow() + timedelta(hours=12)

# whether to get elevation
getElev = False

# specify a specific area/grid to use
area = "conus"

startTime = int(time() * 1000)

analysis = ndfd.get_forecast_analysis(
    var, lat, lon, elev=True, time_step=time_step, area="conus"
)
# analysis = ndfd.get_weather_analysis(
#     lat, lon, time_step=time_step, minTime=minTime, maxTime=maxTime
# )

print("\n**********")
print("Var: " + str(analysis["var"]))
print("Units: " + str(analysis["units"]))
print("Distance: " + str(analysis["distance"]))
print("Forecast Time: " + str(analysis["forecastTime"]))
print("Max: " + str(analysis["max"]))
print("Min: " + str(analysis["min"]))
print("Mean: " + str(analysis["mean"]))
# print('Elev: ' + str(analysis['elevation']['nearest']))
print("stdDev: " + str(analysis["stdDev"]))
print("**********\n")

for t in sorted(analysis["forecasts"]):
    forecast = analysis["forecasts"][t]
    print("{0}: {1}".format(str(t), k_to_f(forecast["nearest"])))
    # print(
    #     '\n{0}:\n{1}\n{2}\nwx:{3}\nVis: {4}'.format(
    #         str(t),
    #         forecast['advisoryString'],
    #         forecast['weatherString'],
    #         forecast['wxString'],
    #         forecast['visibility']
    #     )
    # )

print("\nElapsed: " + str(int(time() * 1000) - startTime))
