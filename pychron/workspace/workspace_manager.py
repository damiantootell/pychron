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
from traits.api import Property, \
    cached_property, Event, List
# ============= standard library imports ========================
import shutil
from git import GitCommandError
import yaml
import os
# ============= local library imports  ==========================
from pychron.core.helpers.filetools import list_directory2, fileiter
from pychron.processing.repository.git.repo_manager import RepoManager


class Manifest(object):
    def __init__(self, p):
        p = os.path.join(p, 'MANIFEST')
        if not os.path.isfile(p):
            with open(p, 'w'):
                pass
        self.path = p

    def add(self, name):
        with open(self.path, 'a') as fp:
            fp.write('{}\n'.format(name))

    def remove(self, name):
        with open(self.path, 'w') as fp:
            for line in fileiter(self.path):
                if line == name:
                    continue
                else:
                    fp.write('{}\n'.format(line))

    @property
    def names(self):
        with open(self.path, 'r') as fp:
            return list(fileiter(fp, strip=True))


class WorkspaceManager(RepoManager):

    # index_db = Instance(IndexAdapter)
    # test = Button

    dclicked = Event
    repo_updated=Event
    commits = List

    def open_repo(self, name, root=None):
        super(WorkspaceManager, self).open_repo(name, root)

        #init manifest object
        self._manifest = Manifest(self.path)

    def find_existing(self, names):
        return [ni for ni in self._manifest.names if ni in names]

    def add_to_manifest(self, path):
        self._manifest.add(os.path.basename(path))

    def add_analysis(self, path, commit=True, message=None, **kw):
        """
            path: absolute path to flat file
            commit: commit changes
            message: message to use for commit


            1. copy file at path to the repository
            2. add record to index

        """

        repo = self._repo

        #copy file to repo
        dest = os.path.join(repo.working_dir, os.path.basename(path))
        if not os.path.isfile(dest):
            shutil.copyfile(path, dest)

        #add to master changeset
        index = repo.index
        index.add([dest])
        if commit:
            if message is None:
                message = 'added record {}'.format(path)
            index.commit(message)

            # if 'working' in repo.branches:
            #     working = repo.heads.working
            # else:
            #     working = repo.create_head('working')
            #
            # working.commit = repo.head.commit

        self.repo_updated=True
        #add to sqlite index
        # im = self.index_db
        # im.add(repo=repo.working_dir, **kw)

    def modify_record(self, path, message=None):
        """
            commit the modification to path to the working branch
        """
        repo = self._repo

        repo.heads.working.checkout()

        index = repo.index
        index.add([path])

        if message is None:
            message = 'modified record {}'.format(path)
        index.commit(message)

    def commit_modification(self):
        """
            set the current working commit to the master head
        """
        repo = self._repo

        master = repo.heads.master
        master.commit = repo.head.commit
        master.checkout()

    def schema_diff(self, attrs):
        """
            show the diff for the given schema keyword `attr` between the working and master
        """
        repo = self._repo
        master_commit = repo.heads.master.commit
        working_commit = repo.heads.working.commit

        ds = working_commit.diff(master_commit, create_patch=True)
        # ds = working_commit.diff(master_commit)

        if not isinstance(attrs, (tuple, list)):
            attrs = (attrs, )

        attr_diff = {}
        for ci in ds.iter_change_type('M'):
            a = ci.a_blob.data_stream

            ayd = yaml.load(a)
            # print 'a', a.read()
            b = ci.b_blob.data_stream

            byd = yaml.load(b)
            for attr in attrs:

                try:
                    av = ayd[attr]
                except KeyError:
                    av = None

                try:
                    bv = byd[attr]
                except KeyError:
                    bv = None

                attr_diff[attr] = av == bv, av, bv

        return attr_diff

    def _load_file_history(self, p):
        repo = self._repo
        try:
            hexshas = repo.git.log('--pretty=%H', '--follow', '--', p).split('\n')
            cs = [repo.rev_parse(c).message for c in hexshas]
            self.commits = cs
        except GitCommandError:
            self.commits = []

    def _dclicked_fired(self, new):
        if new:
            self._load_file_history(new)


class ArArWorkspaceManager(WorkspaceManager):
    nanalyses = Property(depends_on='path, repo_updated')

    @cached_property
    def _get_nanalyses(self):
        return len(list_directory2(self.path, extension='.yaml'))

#============= EOF =============================================