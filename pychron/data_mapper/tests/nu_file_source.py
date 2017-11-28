# ===============================================================================
# Copyright 2016 ross
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

# ============= standard library imports ========================
import os
import unittest

from pychron.data_mapper.sources.nu_source import NuFileSource
from pychron.data_mapper.tests import fget_data_dir


class NuFileSourceUnittest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = NuFileSource()
        p = os.path.join(fget_data_dir(), 'Data_NAG1072.RUN')
        pnice = os.path.join(fget_data_dir(), 'wiscar.nice')
        cls.spec = cls.src.get_analysis_import_spec(p, pnice)

    # def test_runid(self):
    #     self.assertEqual(self.spec.run_spec.runid, '16F0203A')
    #
    # def test_irradiation(self):
    #     self.assertEqual(self.spec.run_spec.irradiation, 'IRR351')
    #
    # def test_level(self):
    #     self.assertEqual(self.spec.run_spec.irradiation_level, 'OQ')
    #
    # def test_sample(self):
    #     self.assertEqual(self.spec.run_spec.sample, 'TM-13-04')
    #
    # def test_material(self):
    #     self.assertEqual(self.spec.run_spec.material, 'Andesite')
    #
    # def test_project(self):
    #     self.assertEqual(self.spec.run_spec.project, 'Pagan')
    #
    # def test_j(self):
    #     self.assertEqual(self.spec.j, 0.000229687907897)
    #
    # def test_j_err(self):
    #     self.assertEqual(self.spec.j_err, 0.00000055732)

    def test_timestamp(self):
        ts = self.spec.run_spec.analysis_timestamp
        self.assertEqual(ts.month, 6)

    def test_xs(self):
        a = self.spec.isotope_group.isotopes['Ar40'].xs
        b = self.spec.isotope_group.isotopes['Ar39'].xs
        self.assertTrue((a == b).all())

    def test_xs2(self):
        a = self.spec.isotope_group.isotopes['Ar40'].xs
        b = self.spec.isotope_group.isotopes['Ar38'].xs
        self.assertFalse((a == b).any())

    def test_40_vals(self):
        a = self.spec.isotope_group.isotopes['Ar40'].ys[0]
        self.assertAlmostEqual(a, 2208.095, 3)

    def test_38_vals(self):
        a = self.spec.isotope_group.isotopes['Ar38'].ys[0]
        self.assertAlmostEqual(a, 17.1000198, 7)

    def test_40_count_xs(self):
        self._test_count_xs('Ar40', 200)

    #
    def test_40_count_ys(self):
        self._test_count_ys('Ar40', 200)

    #
    def test_39_count_xs(self):
        self._test_count_xs('Ar39', 200)

    #
    # def test_39_count_ys(self):
    #     self._test_count_ys('Ar39', 40)
    #
    # def test_38_count_xs(self):
    #     self._test_count_xs('Ar38', 5)
    #
    # def test_38_count_ys(self):
    #     self._test_count_ys('Ar38', 5)
    #
    # def test_37_count_xs(self):
    #     self._test_count_xs('Ar37', 5)
    #
    # def test_37_count_ys(self):
    #     self._test_count_ys('Ar37', 5)
    #
    # def test_36_count_xs(self):
    #     self._test_count_xs('Ar36', 80)
    #
    # def test_36_count_ys(self):
    #     self._test_count_ys('Ar36', 80)
    #
    def _test_count_xs(self, k, cnt):
        xs = self.spec.isotope_group.isotopes[k].xs
        self.assertEqual(len(xs), cnt)

    def _test_count_ys(self, k, cnt):
        ys = self.spec.isotope_group.isotopes[k].ys
        self.assertEqual(len(ys), cnt)
        #
        # def test_discrimination(self):
        #     disc = self.spec.discrimination
        #     self.assertEqual(disc, 1.0505546075085326)


if __name__ == '__main__':
    unittest.main()

# ============= EOF =============================================