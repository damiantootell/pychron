# ===============================================================================
# Copyright 2015 Jake Ross
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

from __future__ import absolute_import
from __future__ import print_function
import os
import shutil
import time
from datetime import datetime
from uncertainties import ufloat, std_dev
# ============= enthought library imports =======================
from traits.api import Bool

from pychron.canvas.utils import iter_geom
from pychron.core.helpers.datetime_tools import ISO_FORMAT_STR
from pychron.core.helpers.filetools import list_directory2, add_extension, \
    list_directory
from pychron.dvc import dvc_dump, dvc_load
from pychron.git_archive.repo_manager import GitRepoManager
from pychron.paths import paths, r_mkdir
from pychron.pychron_constants import INTERFERENCE_KEYS, RATIO_KEYS, DEFAULT_MONITOR_NAME
from pychron import json
import six
from six.moves import map


class MetaObject(object):
    def __init__(self, path, new=False):
        self.path = path
        if os.path.isfile(path):
            with open(path, 'r') as rfile:
                self._load_hook(path, rfile)
        elif not new:
            print('failed loading {} {}'.format(path, os.path.isfile(path)))

    def _load_hook(self, path, rfile):
        pass


class Gains(MetaObject):
    gains = None

    def __init__(self, *args, **kw):
        self.gains = {}
        super(Gains, self).__init__(*args, **kw)

    def _load_hook(self, path, rfile):
        self.gains = json.load(rfile)


def irradiation_holder_holes(name):
    p = os.path.join(paths.meta_root, 'irradiation_holders', add_extension(name))
    holder = IrradiationHolder(p)
    return holder.holes


def irradiation_chronology(name):
    p = os.path.join(paths.meta_root, name, 'chronology.txt')
    return Chronology(p)


def dump_chronology(path, doses):
    if doses is None:
        doses = []

    with open(path, 'w') as wfile:
        for p, s, e in doses:
            if not isinstance(s, str):
                s = s.strftime(ISO_FORMAT_STR)
            if not isinstance(s, str):
                s = s.strftime(ISO_FORMAT_STR)
            if not isinstance(p, str):
                p = '{:0.3f}'.format(p)

            line = '{},{},{}\n'.format(p, s, e)
            wfile.write(line)


class Chronology(MetaObject):
    _doses = None
    duration = 0

    def __init__(self, *args, **kw):
        self._doses = []
        super(Chronology, self).__init__(*args, **kw)

        # @classmethod
        # def dump(cls, path, doses):
        # if doses is None:
        #     doses = []
        #
        # with open(path, 'w') as wfile:
        #     for p, s, e in doses:
        #         if not isinstance(s, str):
        #             s = s.strftime(ISO_FORMAT_STR)
        #         if not isinstance(s, str):
        #             s = s.strftime(ISO_FORMAT_STR)
        #         if not isinstance(p, str):
        #             p = '{:0.3f}'.format(p)
        #
        #         line = '{},{},{}\n'.format(p, s, e)
        #         wfile.write(line)

    def _load_hook(self, path, rfile):
        self._doses = []
        d = 0
        for line in rfile:
            power, start, end = line.strip().split(',')
            start = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime(end, '%Y-%m-%d %H:%M:%S')
            ds = (end - start).total_seconds()
            d += ds
            self._doses.append((float(power), start, end))

        self.duration = d / 3600.

    def get_doses(self):
        return self._doses

    def get_chron_segments(self, analts):
        convert_days = lambda x: x.total_seconds() / (60. * 60 * 24)

        return [(p, convert_days(en - st), convert_days(analts - st)) for p, st, en in self._doses]

    @property
    def total_duration_seconds(self):
        dur = 0
        for pwr, st, en in self._doses:
            dur += (en - st).total_seconds()
        return dur

    @property
    def irradiation_time(self):
        try:
            d_o = self._doses[0][1]
            return time.mktime(d_o.timetuple())
        except IndexError:
            return 0

    @property
    def start_date(self):
        """
            return date component of dose.
            dose =(pwr, %Y-%m-%d %H:%M:%S, %Y-%m-%d %H:%M:%S)

        """
        # doses = self.get_doses(tofloat=False)
        # d = datetime.strptime(doses[0][1], '%Y-%m-%d %H:%M:%S')
        # return d.strftime('%m-%d-%Y')
        # d = datetime.strptime(doses[0][1], '%Y-%m-%d %H:%M:%S')
        date = ''
        doses = self.get_doses()
        if doses:
            d = doses[0][1]
            date = d.strftime('%m-%d-%Y')
        return date


class Production2(MetaObject):
    name = ''
    note = ''

    def _load_hook(self, path, rfile):
        self.name = os.path.splitext(os.path.basename(path))[0]
        attrs = []
        for line in rfile:
            if line.startswith('#-----'):
                break
            k, v, e = line.split(',')
            setattr(self, k, float(v))
            setattr(self, '{}_err'.format(k), float(e))
            attrs.append(k)

        self.attrs = attrs
        self.note = rfile.read()

    def to_dict(self, keys):
        return {t: ufloat(getattr(self, t), getattr(self, '{}_err'.format(t))) for t in keys}
        # return {t: getattr(self, t) for a in keys for t in (a, '{}_err'.format(a))}

    def dump(self):
        with open(self.path, 'w') as wfile:
            for a in self.attrs:
                row = ','.join(map(str, (a, getattr(self, a), getattr(self, '{}_err'.format(a)))))
                wfile.write('{}\n'.format(row))


class Production(MetaObject):
    name = ''
    note = ''
    reactor = 'Triga'
    attrs = None

    @property
    def k_ca(self):
        return 1 / self.Ca_K

    @property
    def k_cl(self):
        return 1 / self.Cl_K

    @property
    def k_cl_err(self):
        return std_dev(1 / ufloat(self.Cl_K, self.Cl_K_err))

    @property
    def k_ca_err(self):
        return std_dev(1 / ufloat(self.Ca_K, self.Ca_K_err))

    def _load_hook(self, path, rfile):
        self.name = os.path.splitext(os.path.basename(path))[0]
        obj = json.load(rfile)

        attrs = []
        for k, v in six.iteritems(obj):
            if k == 'reactor':
                self.reactor = v
            else:
                setattr(self, k, float(v[0]))
                setattr(self, '{}_err'.format(k), float(v[1]))
                attrs.append(k)

        self.attrs = attrs

    def update(self, d):
        if self.attrs is None:
            self.attrs = []

        if isinstance(d, dict):
            for k, v in six.iteritems(d):
                setattr(self, k, v)
                if not k.endswith('_err') and k not in self.attrs:
                    self.attrs.append(k)
        else:
            attrs = []
            for k in INTERFERENCE_KEYS + RATIO_KEYS:
                attrs.append(k)
                v = getattr(d, k)
                if v is None:
                    v = (0, 0)
                setattr(self, k, v[0])
                setattr(self, '{}_err'.format(k), v[1])
            self.attrs = attrs

    def to_dict(self, keys):
        return {t: ufloat(getattr(self, t),
                          getattr(self, '{}_err'.format(t)),
                          tag=t) for t in keys}

    def dump(self, path=None):
        if path is None:
            path = self.path

        obj = {}
        for a in self.attrs:
            obj[a] = (getattr(self, a), getattr(self, '{}_err'.format(a)))
        dvc_dump(obj, path)


class BaseHolder(MetaObject):
    holes = None

    def _load_hook(self, path, rfile):
        holes = []

        line = next(rfile)
        _, radius = line.split(',')
        radius = float(radius)

        for c, line in enumerate(rfile):
            args = line.split(',')
            if len(args) == 2:
                x, y = args
                r = radius
            else:
                x, y, r = args

            holes.append((float(x), float(y), float(r), str(c + 1)))

        self.holes = holes


class LoadHolder(BaseHolder):
    pass


class IrradiationHolder(BaseHolder):
    pass


class Cached(object):
    def __init__(self, clear=None):
        self.clear = clear

    def __call__(self, func):
        def wrapper(obj, name, *args, **kw):
            ret = None
            if not hasattr(obj, '__cache__') or obj.__cache__ is None:
                obj.__cache__ = {}

            cache = obj.__cache__[func] if func in obj.__cache__ else {}
            if self.clear:
                if getattr(obj, self.clear):
                    cache = {}

            key = (func, name)
            force = kw.get('force', None)
            if not force:
                ret = cache.get(key)

            if ret is None:
                ret = func(obj, name, *args, **kw)

            cache[key] = ret
            obj.__cache__[func] = cache
            return ret

        return wrapper


cached = Cached


class MetaRepo(GitRepoManager):
    clear_cache = Bool

    def get_molecular_weights(self):
        p = os.path.join(paths.meta_root, 'molecular_weights.json')
        return dvc_load(p)

    def update_molecular_weights(self, wts, commit=False):
        p = os.path.join(paths.meta_root, 'molecular_weights.json')
        dvc_dump(wts, p)
        self.add(p, commit=commit)

    def add_unstaged(self, *args, **kw):
        super(MetaRepo, self).add_unstaged(self.path, **kw)

    def save_gains(self, ms, gains_dict):
        p = self._gain_path(ms)
        dvc_dump(gains_dict, p)

        if self.add_paths(p):
            self.commit('Updated gains')

    def update_script(self, rootname, name, path_or_blob):
        self._update_text(os.path.join('scripts', rootname.lower()), name, path_or_blob)

    def update_experiment_queue(self, rootname, name, path_or_blob):
        self._update_text(os.path.join('experiments', rootname.lower()), name, path_or_blob)

    def update_level_production(self, irrad, name, prname):
        prname = prname.replace(' ', '_')

        pathname = add_extension(prname, '.json')

        src = os.path.join(paths.meta_root, irrad, 'productions', pathname)
        if os.path.isfile(src):
            self.update_productions(irrad, name, prname)
        # elif prname.startswith('Global'):
        #     prname = prname[7:]
        #     pathname = add_extension(prname, '.json')
        #     src = os.path.join(paths.meta_root, 'productions', pathname)
        #     if os.path.isfile(src):
        #         dest = os.path.join(paths.meta_root, irrad, 'productions', pathname)
        #         if not os.path.isfile(dest):
        #             shutil.copyfile(src, dest)
        #         self.update_productions(irrad, name, prname)
        #     else:
        #         self.warning_dialog('Invalid production name'.format(prname))
        else:
            self.warning_dialog('Invalid production name'.format(prname))

    def add_production_to_irradiation(self, irrad, name, params, add=True, commit=False, new=False):
        self.debug('adding production {} to irradiation={}'.format(name, irrad))
        p = os.path.join(paths.meta_root, irrad, 'productions', add_extension(name, '.json'))
        prod = Production(p, new=new)

        prod.update(params)
        prod.dump()
        if add:
            self.add(p, commit=commit)

    def add_production(self, irrad, name, obj, commit=False, add=True):
        p = self.get_production(irrad, name, force=True)

        p.attrs = attrs = INTERFERENCE_KEYS + RATIO_KEYS
        kef = lambda x: '{}_err'.format(x)

        if obj:
            def values():
                return ((k, getattr(obj, k), kef(k), getattr(obj, kef(k))) for k in attrs)
        else:
            def values():
                return ((k, 0, kef(k), 0) for k in attrs)

        for k, v, ke, e in values():
            setattr(p, k, v)
            setattr(p, ke, e)

        p.dump()
        if add:
            self.add(p.path, commit=commit)

    def update_production(self, prod, irradiation=None):
        ip = self.get_production(prod.name)
        self.debug('saving production {}'.format(prod.name))

        params = prod.get_params()
        for k, v in six.iteritems(params):
            self.debug('setting {}={}'.format(k, v))
            setattr(ip, k, v)

        ip.note = prod.note

        self.add(ip.path, commit=False)
        self.commit('updated production {}'.format(prod.name))

    def update_productions(self, irrad, level, production, add=True):
        p = os.path.join(paths.meta_root, irrad, 'productions.json')

        obj = dvc_load(p)
        if level in obj:
            if obj[level] != production:
                self.debug('setting production to irrad={}, level={}, prod={}'.format(irrad, level,
                                                                                      production))
                obj[level] = production
                dvc_dump(obj, p)

                if add:
                    self.add(p, commit=False)
        else:
            obj[level] = production
            dvc_dump(obj, p)
            if add:
                self.add(p, commit=False)

    def set_identifier(self, irradiation, level, pos, identifier):
        p = self.get_level_path(irradiation, level)
        jd = dvc_load(p)
        positions = self._get_level_positions(irradiation, level)
        d = next((p for p in positions if p['position'] != pos), None)
        if d:
            d['identifier'] = identifier

        dvc_dump(jd, p)
        self.add(p, commit=False)

    def get_level_path(self, irrad, level):
        return os.path.join(paths.meta_root, irrad, '{}.json'.format(level))

    def add_level(self, irrad, level, add=True):
        p = self.get_level_path(irrad, level)
        l = dict(z=0, positions=[])
        dvc_dump(l, p)
        if add:
            self.add(p, commit=False)

    def add_chronology(self, irrad, doses, add=True):
        p = os.path.join(paths.meta_root, irrad, 'chronology.txt')

        # Chronology.dump(p, doses)
        dump_chronology(p, doses)
        if add:
            self.add(p, commit=False)

    def add_irradiation(self, name):
        p = os.path.join(paths.meta_root, name)
        if not os.path.isdir(p):
            os.mkdir(p)

    def add_position(self, irradiation, level, pos, add=True):
        p = self.get_level_path(irradiation, level)
        jd = dvc_load(p)
        if isinstance(jd, list):
            positions = jd
            z = 0
        else:
            positions = jd.get('positions', [])
            z = jd.get('z', 0)

        pd = next((p for p in positions if p['position'] == pos), None)
        if pd is None:
            positions.append({'position': pos, 'decay_constants': {}})
        # for pd in jd:
        #     if pd['position'] == pos:

        # njd = [ji if ji['position'] != pos else {'position': pos, 'j': j, 'j_err': e,
        #                                          'decay_constants': decay,
        #                                          'identifier': identifier,
        #                                          'analyses': [{'uuid': ai.uuid,
        #                                                        'record_id': ai.record_id,
        #                                                        'status': ai.is_omitted()}
        #                                                       for ai in analyses]} for ji in jd]

        dvc_dump({'z': z, 'positions': positions}, p)
        if add:
            self.add(p, commit=False)

    def add_irradiation_holder(self, name, blob, commit=False, overwrite=False, add=True):
        root = os.path.join(paths.meta_root, 'irradiation_holders')
        if not os.path.isdir(root):
            os.mkdir(root)
        p = os.path.join(root, add_extension(name))

        if not os.path.isfile(p) or overwrite:
            with open(p, 'w') as wfile:
                holes = list(iter_geom(blob))
                n = len(holes)
                wfile.write('{},0.0175\n'.format(n))
                for idx, (x, y, r) in holes:
                    wfile.write('{:0.4f},{:0.4f},{:0.4f}\n'.format(x, y, r))
            if add:
                self.add(p, commit=commit)

    def get_load_holders(self):
        p = os.path.join(paths.meta_root, 'load_holders')
        return list_directory(p, extension='.txt', remove_extension=True)

    def add_load_holder(self, name, path_or_txt, commit=False, add=True):
        p = os.path.join(paths.meta_root, 'load_holders', name)
        if os.path.isfile(path_or_txt):
            shutil.copyfile(path_or_txt, p)
        else:
            with open(p, 'w') as wfile:
                wfile.write(path_or_txt)
        if add:
            self.add(p, commit=commit)

    def update_level_z(self, irradiation, level, z):
        p = self.get_level_path(irradiation, level)
        obj = dvc_load(p)

        try:
            add = obj['z'] != z
            obj['z'] = z
        except TypeError:
            obj = {'z': z, 'positions': obj}
            add = True

        dvc_dump(obj, p)
        if add:
            self.add(p, commit=False)

    def remove_irradiation_position(self, irradiation, level, hole):
        p = self.get_level_path(irradiation, level)
        jd = dvc_load(p)
        if jd:
            if isinstance(jd, list):
                positions = jd
                z = 0
            else:
                positions = jd['positions']
                z = jd['z']

            # njd = [ji for ji in jd if not ji['position'] == hole]
            npositions = [ji for ji in positions if not ji['position'] == hole]
            obj = {'z': z, 'positions': npositions}
            dvc_dump(obj, p)
            self.add(p, commit=False)

    def update_fluxes(self, irradiation, level, j, e, add=True):
        p = self.get_level_path(irradiation, level)
        jd = dvc_load(p)
        print(p)
        print(jd)
        if isinstance(jd, list):
            positions = jd
        else:
            positions = jd.get('positions')

        if positions:
            for ip in positions:
                ip['j'] = j
                ip['j_err'] = e

            dvc_dump(jd, p)
            if add:
                self.add(p, commit=False)

    def update_flux(self, irradiation, level, pos, identifier, j, e, mj, me, decay=None, analyses=None, add=True):
        if decay is None:
            decay = {}
        if analyses is None:
            analyses = []

        p = self.get_level_path(irradiation, level)
        jd = dvc_load(p)
        if isinstance(jd, list):
            positions = jd
            z = 0
        else:
            positions = jd.get('positions', [])
            z = jd.get('z', 0)

        npos = {'position': pos, 'j': j, 'j_err': e,
                'mean_j': mj, 'mean_j_err': me,
                'decay_constants': decay,
                'identifier': identifier,
                'analyses': [{'uuid': ai.uuid,
                              'record_id': ai.record_id,
                              'status': ai.is_omitted()}
                             for ai in analyses]}
        if positions:
            added = any((ji['position'] == pos for ji in positions))
            npositions = [ji if ji['position'] != pos else npos for ji in positions]
            if not added:
                npositions.append(npos)
        else:
            npositions = [npos]

        obj = {'z': z, 'positions': npositions}
        dvc_dump(obj, p)
        if add:
            self.add(p, commit=False)

    def update_chronology(self, name, doses):
        p = self._chron_name(name)
        dump_chronology(p, doses)
        # Chronology.dump(p, doses)

        self.add(p, commit=False)
        # self.meta_commit('updated chronology')
        # self.meta_repo.clear_cache = True
        # if commit:
        #     self.commit('Updated {} chronology'.format(name))
        #     if push:
        #         self.push()

    def get_irradiation_holder_names(self):
        return list_directory2(os.path.join(paths.meta_root, 'irradiation_holders'),
                               extension='.txt',
                               remove_extension=True)

    def get_default_productions(self):
        p = os.path.join(paths.meta_root, 'reactors.json')
        if not os.path.isfile(p):
            with open(p, 'w') as wfile:
                from pychron.file_defaults import REACTORS_DEFAULT
                wfile.write(REACTORS_DEFAULT)

        with open(os.path.join(paths.meta_root, 'reactors.json'), 'r') as rfile:
            return json.load(rfile)

    # def get_irradiation_productions(self):
    #     # list_directory2(os.path.join(paths.meta_dir, 'productions'),
    #     # remove_extension=True)
    #     prs = []
    #     root = os.path.join(paths.meta_root, 'productions')
    #     for di in ilist_directory2(root, extension='.json'):
    #         pr = Production(os.path.join(root, di))
    #         prs.append(pr)
    #     return prs
    def get_flux_positions(self, irradiation, level):
        positions = self._get_level_positions(irradiation, level)
        return positions

    def get_flux(self, irradiation, level, position):
        positions = self.get_flux_from_positions(irradiation, level)
        return self.get_flux_from_positions(position, positions)

    def get_flux_from_positions(self, position, positions):

        # path = os.path.join(paths.meta_root, irradiation, add_extension(level, '.json'))
        j, je, lambda_k = 0, 0, None
        standard_name, standard_material, standard_age = DEFAULT_MONITOR_NAME, 'sanidine', ufloat(28.201, 0)
        # positions = self._get_level_positions(irradiation, level)
        if positions:
            pos = next((p for p in positions if p['position'] == position), None)
            if pos:
                j, je = pos.get('j', 0), pos.get('j_err', 0)
                dc = pos.get('decay_constants')
                if dc:
                    # this was a temporary fix and likely can be removed
                    if isinstance(dc, float):
                        v, e = dc, 0
                    else:
                        v, e = dc.get('lambda_k_total', 0), dc.get('lambda_k_total_error', 0)
                    lambda_k = ufloat(v, e)
                mon = pos.get('monitor')
                if mon:
                    standard_name = mon.get('name', DEFAULT_MONITOR_NAME)
                    sa = mon.get('age', 28.201)
                    se = mon.get('error', 0)
                    standard_age = ufloat(sa, se, tag='standard_age')
                    standard_material = mon.get('material', 'sanidine')

        fd = {'j': ufloat(j, je, tag='J'), 'lambda_k': lambda_k,
              'standard_name': standard_name,
              'standard_material': standard_material,
              'standard_age': standard_age}
        return fd

    def get_gains(self, name):
        g = self.get_gain_obj(name)
        return g.gains

    def _gain_path(self, name):
        root = os.path.join(paths.meta_root, 'spectrometers')
        if not os.path.isdir(root):
            os.mkdir(root)

        p = os.path.join(root, add_extension('{}.gain'.format(name), '.json'))
        return p

    @cached('clear_cache')
    def get_gain_obj(self, name, **kw):
        p = self._gain_path(name)
        return Gains(p)

    # @cached('clear_cache')
    def get_production(self, irrad, level, **kw):
        path = os.path.join(paths.meta_root, irrad, 'productions.json')
        obj = dvc_load(path)
        pname = obj[level]
        p = os.path.join(paths.meta_root, irrad, 'productions', add_extension(pname, ext='.json'))

        ip = Production(p)
        # print 'new production id={}, name={}, irrad={}, level={}'.format(id(ip), pname, irrad, level)
        return pname, ip

    # @cached('clear_cache')
    def get_chronology(self, name, **kw):
        return irradiation_chronology(name)

    @cached('clear_cache')
    def get_irradiation_holder_holes(self, name, **kw):
        return irradiation_holder_holes(name)

    @cached('clear_cache')
    def get_load_holder_holes(self, name, **kw):
        p = os.path.join(paths.meta_root, 'load_holders', add_extension(name))
        holder = LoadHolder(p)
        return holder.holes

    # private
    def _get_level_positions(self, irrad, level):
        p = self.get_level_path(irrad, level)
        obj = dvc_load(p)
        if isinstance(obj, list):
            positions = obj
        else:
            positions = obj.get('positions', [])
        return positions

    def _chron_name(self, name):
        return os.path.join(paths.meta_root, name, 'chronology.txt')

    def _update_text(self, tag, name, path_or_blob):
        if not name:
            self.debug('cannot update text with no name. tag={} name={}'.format(tag, name))
            return

        root = os.path.join(paths.meta_root, tag)
        if not os.path.isdir(root):
            r_mkdir(root)

        p = os.path.join(root, name)
        if os.path.isfile(path_or_blob):
            shutil.copyfile(path_or_blob, p)
        else:
            with open(p, 'w') as wfile:
                wfile.write(path_or_blob)

        self.add(p, commit=False)

# ============= EOF =============================================
