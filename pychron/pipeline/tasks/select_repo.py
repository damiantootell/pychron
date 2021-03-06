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

# ============= enthought library imports =======================
from __future__ import absolute_import
from traits.api import HasTraits, Str, List
# ============= standard library imports ========================
# ============= local library imports  ==========================
from traitsui.api import View, UItem, EnumEditor


class SelectExperimentIDView(HasTraits):
    selected = Str
    available = List

    traits_view = View(UItem('selected',
                             width=250,
                             editor=EnumEditor(name='available')),
                       buttons=['OK', 'Cancel'],
                       width=300,
                       title='Select Experiment')

# ============= EOF =============================================
