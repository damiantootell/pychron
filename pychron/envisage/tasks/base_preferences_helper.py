# ===============================================================================
# Copyright 2013 Jake Ross
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
from __future__ import absolute_import
from __future__ import print_function
import re

from apptools.preferences.api import PreferencesHelper
from envisage.ui.tasks.preferences_pane import PreferencesPane
from traits.api import List, Button, Any, Int, Str, Enum, Color, String, Property, BaseStr
from traitsui.api import View, VGroup, UItem, HGroup, Item
from traitsui.list_str_adapter import ListStrAdapter

from pychron.core.ui.custom_label_editor import CustomLabel
from pychron.envisage.icon_button_editor import icon_button_editor
from six.moves import map
import six
from six.moves import zip


class FavoritesAdapter(ListStrAdapter):
    columns = [('', 'name')]
    can_edit = False

    def get_text(self, obj, tr, ind):
        o = getattr(obj, tr)[ind]
        return o.split(',')[0]


class BasePreferencesHelper(PreferencesHelper):
    pass
    # def _get_value(self, name, value):
    #     if 'color' in name:
    #         print name, value, type(value)
    #
    #         pass
    #         # print name, value, type(value)
    #         # value = extract_color(value)
    #         # try:
    #         #     value = extract_color
    #         #     # value = value.split('(')[1]
    #         #     # value = value[:-1]
    #         #     # value = map(float, value.split(','))
    #         #     # value = ','.join(map(lambda x: str(int(x * 255)), value))
    #         # except IndexError:
    #         #     value = super(BasePreferencesHelper, self)._get_value(name, value)
    #     else:
    #         value = super(BasePreferencesHelper, self)._get_value(name, value)
    #     return value


REPO_REGEX = re.compile(r'^\w+[\w\-\_]*\/\w+$')


def test_connection_item():
    return icon_button_editor('test_connection', 'server-connect',
                              tooltip='Test connection to Github Repo')


def remote_status_item(label=None):
    grp = HGroup(Item('remote',
                      label='Name', springy=True),
                 test_connection_item(),
                 CustomLabel('_remote_status',
                             width=50,
                             color_name='_remote_status_color'))
    if label:
        grp.label = label
        grp.show_border = True
    return grp


class RepoString(BaseStr):

    def validate(self, obj, name, value):
        if REPO_REGEX.match(value):
            return value
        else:
            self.error(obj, name, value)


class GitRepoPreferencesHelper(BasePreferencesHelper):
    # remote = Property(String, depends_on='_remote')
    #    _remote = String
    remote = RepoString
    test_connection = Button
    _remote_status = Str
    _remote_status_color = Color

    def _test_connection_fired(self):
        import six.moves.urllib.request, six.moves.urllib.error, six.moves.urllib.parse

        print('fffff', self.remote)
        if self.remote.strip():
            try:
                cmd = 'https://github.com/{}.git'.format(self.remote)
                six.moves.urllib.request.urlopen(cmd)
                self._remote_status = 'Valid'
                self._remote_status_color = 'green'
                self._connection_hook()
                return
            except BaseException as e:
                print('exception', e, cmd)

        self._remote_status_color = 'red'
        self._remote_status = 'Invalid'

    def _connection_hook(self):
        pass

    # def _set_remote(self, v):
    #     if v is not None:
    #         self._remote = v
    #
    # def _get_remote(self):
    #     return self._remote
    #
    # def _validate_remote(self, v):
    #     if not v.strip():
    #         return ''
    #
    #     if REPO_REGEX.match(v):
    #         return v


class FavoritesPreferencesHelper(BasePreferencesHelper):
    favorites = List
    fav_name = Str

    add_favorite = Button('+')
    delete_favorite = Button('-')
    selected = Any
    selected_index = Int

    def _is_preference_trait(self, trait_name):
        if trait_name == 'favorites_items':
            return False
        else:
            return super(FavoritesPreferencesHelper, self)._is_preference_trait(trait_name)

    def _get_attrs(self):
        raise NotImplementedError

    def _get_values(self):
        raise NotImplementedError

    def _selected_changed(self):
        sel = self.selected
        if isinstance(sel, (str, six.text_type)):
            vs = sel.split(',')
            for v, attr in zip(vs, self._get_attrs()):
                setattr(self, attr, str(v))
        self._selected_change_hook()

    def _selected_change_hook(self):
        pass

    def _delete_favorite_fired(self):
        if self.selected:
            if self.favorites:
                if self.selected in self.favorites:
                    self.favorites.remove(self.selected)

            if self.favorites:
                self.selected = self.favorites[-1]
            else:
                vs = ['', '---', '', '', '', '']
                for v, attr in zip(vs, self._get_attrs()):
                    setattr(self, attr, str(v))

    def _add_favorite_fired(self):
        if self.fav_name:
            fv = ','.join(map(str, self._get_values()))
            pf = next((f for f in self.favorites
                       if f.split(',')[0] == self.fav_name), None)
            if pf:
                ind = self.favorites.index(pf)
                self.favorites.remove(pf)
                self.favorites.insert(ind, fv)

            else:
                self.favorites.append(fv)

            self.selected = fv


class BaseConsolePreferences(BasePreferencesHelper):
    fontsize = Enum(6, 8, 10, 11, 12, 14, 16, 18, 22, 24, 36)

    textcolor = Color('green')
    bgcolor = Color('black')

    preview = Str('Pychron is python + geochronology')


class BaseConsolePreferencesPane(PreferencesPane):
    category = 'Console'
    label = ''

    def traits_view(self):
        preview = CustomLabel('preview',
                              size_name='fontsize',
                              color_name='textcolor',
                              bgcolor_name='bgcolor')

        v = View(VGroup(HGroup(UItem('fontsize'),
                               UItem('textcolor'),
                               UItem('bgcolor')),
                        preview,
                        show_border=True,
                        label=self.label))
        return v
# ============= EOF =============================================
