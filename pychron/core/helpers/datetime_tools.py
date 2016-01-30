# ===============================================================================
# Copyright 2011 Jake Ross
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ===============================================================================

import time
import math

from datetime import datetime
from numpy import ediff1d, asarray
from numpy import where

ISO_FORMAT_STR = "%Y-%m-%d %H:%M:%S"


def time_generator(start=None):
    if start is None:
        start = time.time()
    while 1:
        yield time.time() - start


def generate_datetimestamp(resolution='seconds'):
    """
    """
    ti = time.time()
    if resolution == 'seconds':
        r = time.strftime(ISO_FORMAT_STR)
    else:
        millisecs = math.modf(ti)[0] * 1000
        r = '{}{:0.5f}'.format(time.strftime(ISO_FORMAT_STR), millisecs)
    return r


def generate_datestamp():
    return get_date()


def get_datetime(timestamp=None):
    if timestamp is None:
        timestamp = time.time()

    if isinstance(timestamp, float):
        d = datetime.fromtimestamp(timestamp)
    else:
        d = datetime.strptime(timestamp, ISO_FORMAT_STR)
    return d


def get_date():
    return time.strftime('%Y-%m-%d')


def make_timef(timestamp=None):
    if timestamp is None:
        t = time.time()
    elif isinstance(timestamp, float):
        t = timestamp
        # timestamp = datetime.fromtimestamp(timestamp)
    else:
        t = time.mktime(timestamp.timetuple())

    return t


def convert_timestamp(timestamp, fmt=None):
    if fmt is None:
        fmt = ISO_FORMAT_STR
    t = get_datetime(timestamp)
    return datetime.strftime(t, fmt)


#    return time.mktime(t.timetuple()) + 1e-6 * t.microsecond
# def convert_float(timestamp):

def diff_timestamp(end, start=0):
    if not isinstance(end, datetime):
        end = datetime.fromtimestamp(end)
    if not isinstance(start, datetime):
        start = datetime.fromtimestamp(start)
    t = end - start
    h = t.seconds / 3600
    m = (t.seconds % 3600) / 60
    s = (t.seconds % 3600) % 60

    return t, h, m, s


def bin_timestamps(ts, tol_hrs=1):
    ts = asarray(ts)
    tol = 60 * 60 * tol_hrs
    dts = ediff1d(ts)
    # print dts
    idxs = where(dts > tol)[0]
    return idxs
