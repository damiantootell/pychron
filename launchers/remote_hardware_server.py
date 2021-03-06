#!/usr/bin/python
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
from __future__ import absolute_import
from traits.etsconfig.etsconfig import ETSConfig

ETSConfig.toolkit = 'qt4'
import os


def build_directories():
    from pychron.paths import r_mkdir, paths
    root=os.path.join(os.path.expanduser('~'), 'RHM')

    if not os.path.isdir(root):
        os.mkdir(root)

    # servers = os.path.join(root, 'servers')
    ldir = os.path.join(root, 'log')
    r_mkdir(ldir)
    paths.log_dir = ldir
    paths.root = root


if __name__ == '__main__':

    root = os.path.dirname(__file__)
    from .helpers import add_eggs
    add_eggs(root)

    build_directories()
    from pychron.core.helpers.logger_setup import logging_setup
    from pychron.managers.remote_hardware_server_manager import RemoteHardwareServerManager

    logging_setup('server')
    s = RemoteHardwareServerManager()  # handler_klass=AppHandler)
    s.load()
    s.configure_traits()
    os._exit(0)

#    launch()
# ============= EOF ====================================
#
# def read_configuration():
#    '''
#         read the server initialization file in the initialization dir.
#
#         ex
#         [General]
#         servers= server_names
#
#         server names refer to server configuration files
#    '''
#
#    config = ConfigParser.ConfigParser()
#    path = os.path.join(initialization_dir, 'server_initialization.cfg')
#    config.read(path)
#
#    servernames = config.get('General', 'servers').split(',')
#    return servernames
#
# def launch():
#    '''
#
#    launch the application
#
#    '''
#
#    #create a new CommandRepeater to repeat commands to the ExtractionLine Program on
#    #on the specified port
#    repeater = CommandRepeater(name = 'repeater',
#                              configuration_dir_name = 'servers'
#                              )
#    repeater.bootstrap()
#
#    servers = []
#    for server_name in read_configuration():
#
#        #create a new RemoteCommandServer to handle TCP or UDP Protocol based commands
#        e = RemoteCommandServer(name = server_name,
#                               repeater = repeater,
#                               configuration_dir_name = 'servers',
#                               )
#
#        e.bootstrap()
#        servers.append(e)
#
#    try:
#        while 1:
#        #serve infinitely
#            pass
#    except KeyboardInterrupt:
#        for s in servers:
#            if s is not None:
#                s._server.shutdown()
#        os._exit(0)
