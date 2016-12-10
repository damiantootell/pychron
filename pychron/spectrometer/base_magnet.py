# ===============================================================================
# Copyright 2014 Jake Ross
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ===============================================================================

# ============= enthought library imports =======================
import os
import time
from math import pi

import yaml
from numpy import arange, sin
from traits.api import Property, Float, Event, Instance
from traitsui.api import View, Item, VGroup, HGroup, Spring, RangeEditor

from pychron.loggable import Loggable
from pychron.paths import paths


def get_float(func):
    def dec(*args, **kw):
        try:
            return float(func(*args, **kw))
        except (TypeError, ValueError):
            return 0.0

    return dec


class BaseMagnet(Loggable):
    dac = Property(Float, depends_on='_dac')
    mass = Float

    _dac = Float
    dacmin = Float(0.0)
    dacmax = Float(10.0)

    massmin = Property(Float, depends_on='_massmin')
    massmax = Property(Float, depends_on='_massmax')
    _massmin = Float(0.0)
    _massmax = Float(200.0)

    settling_time = 0.5
    detector = Instance('pychron.spectrometer.base_detector.BaseDetector')

    dac_changed = Event

    mftable = Instance('pychron.spectrometer.mftable.MagnetFieldTable', ())
    confirmation_threshold_mass = Float
    use_deflection_correction = True
    use_af_demagnetization = False

    _suppress_mass_update = False

    def reload_mftable(self):
        self.mftable.load_mftable()

    def set_dac(self, *args, **kw):
        raise NotImplementedError

    def set_mftable(self, name):
        self.mftable.set_path_name(name)

    def update_field_table(self, *args):
        self.mftable.update_field_table(*args)

    # ===============================================================================
    # persistence
    # ===============================================================================
    def load(self):
        pass

    def finish_loading(self):
        """
        initialize the mftable

        read DAC from device
        :return:
        """
        if self.spectrometer:
            molweights = self.spectrometer.molecular_weights
            name = self.spectrometer.name
        else:
            from pychron.spectrometer.molecular_weights import MOLECULAR_WEIGHTS as molweights

            name = ''
        # self.mftable.molweights = molweights
        self.mftable.initialize(molweights)
        self.mftable.spectrometer_name = name.lower()

        d = self.read_dac()
        if d is not None:
            self._dac = d

    # ===============================================================================
    # mapping
    # ===============================================================================
    def map_dac_to_mass(self, dac, detname):
        """
        convert a DAC value (voltage) to mass for a given detector
        use the mftable

        :param dac: float, voltage (0-10V)
        :param detname: str, name of a detector, e.g H1
        :return: float, mass
        """
        return self.mftable.map_dac_to_mass(dac, detname)

    def map_mass_to_dac(self, mass, detname):
        """
        convert a mass value from amu to dac for a given detector

        :param mass: float, amu
        :param detname: std, name of a detector, e.g. H1
        :return: float, dac voltage
        """

        dac = self.mftable.map_mass_to_dac(mass, detname)
        self.debug('{} map mass to dac {} >> {}'.format(detname, mass, dac))

        return dac

    def map_dac_to_isotope(self, dac=None, det=None, current=True):
        """
        convert a dac voltage to isotope name for a given detector


        :param dac: float, voltage
        :param det: str, detector name
        :param current: bool, get current hv
        :return: str, e.g Ar40
        """
        if dac is None:
            dac = self._dac
        if det is None:
            det = self.detector

        if det:
            dac = self.spectrometer.uncorrect_dac(det, dac, current=current)

        m = self.map_dac_to_mass(dac, det.name)
        if m is not None:
            return self.spectrometer.map_isotope(m)
            # molweights = self.spectrometer.molecular_weights
            # return next((k for k, v in molweights.iteritems() if abs(v - m) < 0.001), None)

    def mass_change(self, m):
        """
        set the self.mass attribute
        suppress mass change handler

        :param m: float
        :return:
        """
        self._suppress_mass_update = True
        self.trait_set(mass=m)
        self._suppress_mass_update = False

    # ===============================================================================
    # private
    # ===============================================================================
    def _do_af_demagnetization(self, target, setfunc):
        p = os.path.join(paths.spectrometer_dir, 'af_demagnetization.yaml')
        if os.path.isfile(p):
            with open(p, 'r') as rfile:
                try:
                    yd = yaml.load(rfile)
                except BaseException, e:
                    self.warning('AF Demagnetization unavailable. Syntax error in file. Error: {}'.format(e))
                    return

            period = yd.get('period', None)
            if period is None:
                frequency = yd.get('frequency')
                if frequency is None:
                    self.warning('AF Demagnetization unavailable. '
                                 'Need to specify "period" or "frequency" in {}'.format(p))
                    return
                else:
                    period = 1 / float(frequency)
            else:
                frequency = 1 / float(period)

            duration = yd.get('duration')
            slope = yd.get('slope')
            if duration is None:
                duration = 5
                self.debug('defaulting to duration={}'.format(duration))
            if slope is None:
                slope = 1
                self.debug('defaulting to slope={}'.format(slope))

            sx = arange(pi * 0.5 * period, duration, pi * period)
            dacs = slope * sx * sin(frequency * sx)
            self.info('Doing AF Demagnetization around target={}. '
                      'duration={}, slope={}, period={}'.format(target, duration, slope, period))
            for dac in reversed(dacs):
                self.debug('set af dac raw:{} dac:{}'.format(dac, target + dac))
                setfunc(target + dac)
                time.sleep(period)
        else:
            self.warning('AF Demagnetization unavailable. {} not a valid file'.format(p))

    def _validate_mass_change(self, cm, m):
        ct = self.confirmation_threshold_mass

        move_ok = True
        if abs(cm - m) > ct:
            move_ok = False
            self.info('Requested move greater than threshold. Current={}, Request={}, Threshold={}'.format(cm, m, ct))
            if self.confirmation_dialog('Requested magnet move is greater than threshold.\n'
                                        'Current Mass={}\n'
                                        'Requested Mass={}\n'
                                        'Threshold={}\n'
                                        'Are you sure you want to continue?'.format(cm, m, ct)):
                move_ok = True
        return move_ok

    def _mass_changed(self, old, new):
        if self._suppress_mass_update:
            return

        if self._validate_mass_change(old, new):
            self._set_mass(new)
        else:
            self.mass_change(old)

    def _set_mass(self, m):
        if self.detector:
            self.debug('setting mass {}'.format(m))
            dac = self.map_mass_to_dac(m, self.detector.name)
            dac = self.spectrometer.correct_dac(self.detector, dac)
            self.dac = dac

    # ===============================================================================
    # property get/set
    # ===============================================================================
    def _validate_dac(self, d):
        return self._validate_float(d)

    def _get_dac(self):
        return self._dac

    def _set_dac(self, v):
        if v is not None:
            self.set_dac(v)

    def _validate_float(self, d):
        try:
            return float(d)
        except (ValueError, TypeError):
            return d

    def _validate_massmin(self, d):
        d = self._validate_float(d)
        if isinstance(d, float):
            if d > self.massmax:
                d = str(d)
        return d

    def _get_massmin(self):
        return self._massmin

    def _set_massmin(self, v):
        self._massmin = v

    def _validate_massmax(self, d):
        d = self._validate_float(d)
        if isinstance(d, float):
            if d < self.massmin:
                d = str(d)
        return d

    def _get_massmax(self):
        return self._massmax

    def _set_massmax(self, v):
        self._massmax = v

    # ===============================================================================
    # views
    # ===============================================================================
    def traits_view(self):
        v = View(
            VGroup(
                VGroup(
                    Item('dac', editor=RangeEditor(low_name='dacmin',
                                                   high_name='dacmax',
                                                   format='%0.5f')),

                    Item('mass', editor=RangeEditor(mode='slider', low_name='massmin',
                                                    high_name='massmax',
                                                    format='%0.3f')),
                    HGroup(Spring(springy=False,
                                  width=48),
                           Item('massmin', width=-40), Spring(springy=False,
                                                              width=138),
                           Item('massmax', width=-55),

                           show_labels=False),
                    show_border=True,
                    label='Control')))

        return v

# ============= EOF =============================================
