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

from pyface.tasks.action.schema import SToolBar
from traits.api import Instance

#============= standard library imports ========================
#============= local library imports  ==========================
from pychron.core.codetools.simple_timeit import timethis
from pychron.core.progress import progress_iterator
from pychron.paths import paths
from pychron.processing.export.yaml_analysis_exporter import YamlAnalysisExporter
from pychron.processing.tasks.browser.browser_task import BaseBrowserTask
from pychron.workspace.tasks.actions import NewWorkspaceAction, OpenWorkspaceAction, CheckoutAnalysesAction, \
    AddBranchAction
from pychron.workspace.tasks.panes import WorkspaceCentralPane, WorkspaceControlPane
from pychron.workspace.workspace_manager import ArArWorkspaceManager


class WorkspaceTask(BaseBrowserTask):

    tool_bars = [SToolBar(NewWorkspaceAction(),
                          OpenWorkspaceAction()),
                 SToolBar(CheckoutAnalysesAction(),
                          AddBranchAction())]

    workspace = Instance(ArArWorkspaceManager, ())

    def add_branch(self):
        from pychron.workspace.tasks.new_branch_view import NewBranchView
        nb = NewBranchView()
        info = nb.edit_traits()
        if info.result:
            self.workspace.create_branch(nb.name)

    def checkout_analyses(self):
        if not self.workspace.path:
            return

        self.debug('checking out analyses')
        ans = self.analysis_table.analyses

        #check for existing
        #ask user to selected which files to overwrite
        existing =self.workspace.find_existing(['{}.yaml'.format(ai.record_id) for ai in ans])
        if existing:
            self.debug('Analyses exist in workspace')
            return

        #make dbanalyses
        ans = self.manager.make_analyses(ans)

        #export to yaml files
        exp=YamlAnalysisExporter()

        def func(ai, prog, i, n):
            exp.add(ai)
            p= os.path.join(self.workspace.path,'{}.yaml'.format(ai.record_id))
            exp.destination.destination = p
            # exp.export()
            timethis(exp.export, msg='export')

            #update manifest
            self.workspace.add_to_manifest(p)
            # timethis(self.workspace.add_to_manifest, args=(p,), msg='a')

            #add to repositiory
            #self.workspace.add_analysis(p, commit=False)
            timethis(self.workspace.add_analysis, args=(p,),
                     kwargs={'commit':False},
                     msg='add to git')
            if prog:
                prog.change_message('Added {} to workspace'.format(ai.record_id))

        progress_iterator(ans, func, threshold=1)
        self.workspace.commit('Added Analyses {} to {}'.format(ans[0].record_id,
                                                               ans[-1].record_id))

    def new_workspace(self):
        self.debug('new workspace')

    def open_workspace(self):
        self.debug('open workspace')
        p='/Users/ross/Pychrondata_dev/data/workspaces/test'
        if not os.path.isdir(p):
            p = self.open_directory_dialog(default_directory=paths.workspace_root_dir)

        if p:
            self.workspace.open_repo(p)

    def create_central_pane(self):
        return WorkspaceCentralPane(model=self.workspace)

    def create_dock_panes(self):
        return [WorkspaceControlPane(),
                self._create_browser_pane()]
#============= EOF =============================================

