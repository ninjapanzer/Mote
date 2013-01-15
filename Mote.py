import sublime, sublime_plugin

import subprocess
import os, time, inspect, sys
import threading
import json
import posixpath
import time
import shutil
from collections import deque

# use this if you want to include modules from a subforder
cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],"lib")))
if cmd_subfolder not in sys.path:
    sys.path.insert(0, cmd_subfolder)

import paramiko

MOTES = {}

def main():
    with open('servers.json') as f:
        MOTES = json.load(f)
    for server in MOTES:
        MOTES[server]['thread'] = MoteSearchThread(server,
            connection_string=MOTES[server]['connection_string'],
            idle_recursive = MOTES[server]['idle_recursive'] if 'idle_recursive' in MOTES[server] else False,
            search_path = MOTES[server]['default_path'] if 'default_path' in MOTES[server] else '',
            password = MOTES[server]['password'] if 'password' in MOTES[server] else None,
            private_key = MOTES[server]['private_key'] if 'private_key' in MOTES[server] else None,
            port = MOTES[server]['port'] if 'port' in MOTES[server] else None
            )

    root = os.path.join(sublime.packages_path(),'Mote','temp')
    if os.path.exists(root):
        shutil.rmtree(root)

    return MOTES

def show_commands(window):
    commands = []

    for server in MOTES:
        if MOTES[server]['thread'].sftp == None:
            commands.append({
                "caption": "Mote: Connect - %s" % server,
                "command": "mote_view","args":
                {
                    "server": server
                }
            })
        else:
            commands.append({
                "caption": "Mote: View - %s" % server,
                "command": "mote_view","args":
                {
                    "server": server
                }
            })
            commands.append({
                "caption": "Mote: Disconnect - %s" % server,
                "command": "mote_disconnect","args":
                {
                    "server": server
                }
            })

    #commands.append({
    #    "caption": "Mote: Status",
    #    "command": "mote_status"
    #})

    def show_quick_panel():
        window.show_quick_panel([ x['caption'] for x in commands ], on_select)

    def on_select(picked):
        if picked == -1:
            return

        window.run_command(commands[picked]['command'], commands[picked]['args'])

        #print commands[picked]


    sublime.set_timeout(show_quick_panel, 10)


# External Commands
class MoteCommand(sublime_plugin.WindowCommand):
    def run(self):
        show_commands(self.window)


# Internal Commands
class MoteViewCommand(sublime_plugin.WindowCommand):
    def run(self, server):
        MOTES[server]['thread'].window = self.window
        if MOTES[server]['thread'].sftp == None:
            MOTES[server]['thread'].start()
        else:
            MOTES[server]['thread'].showfilepanel()


class MoteStatusCommand(sublime_plugin.WindowCommand):
    def run(self):
        for server in MOTES:
            print MOTES[server]
            print MOTES[server]['thread'].is_alive()
            print MOTES[server]['thread'].name
            print MOTES[server]['thread'].sftp
            print MOTES[server]['thread'].results


class MoteDisconnectCommand(sublime_plugin.WindowCommand):
    def run(self, server=''):
        MOTES[server]['thread'].add_command('exit','')


# Listeners

class MoteUploadOnSave(sublime_plugin.EventListener):
    def on_post_save(self, view):
        root = os.path.join(sublime.packages_path(),'Mote','temp')
        relpath = os.path.relpath(view.file_name(),root)
        #print relpath
        if relpath[0:2] != '..':
            server = relpath.split(os.sep)[0]
            server_path = posixpath.join(*relpath.split(os.sep)[1:])
            MOTES[server]['thread'].add_command('save',server_path)



class MoteSearchThread(threading.Thread):
    def __init__(self, server, search_path='', connection_string='', password=None, idle_recursive=False, private_key=None, port=None):
        self.server = server
        self.search_path = search_path
        self.hostname = ''
        self.password = password #didn't see this in the namespace so added it
        self.connection_string = connection_string
        self.os_mode = os.name
        self.base_dir = ''

        #Identify if this is a username@hostname string
        connection_string_parts = connection_string.split('@')
        if len(connection_string_parts) > 1:
            self.hostname = connection_string_parts[1]
            self.username = connection_string_parts[0]
        else:
            self.hostname = connection_string

        #lovely debugging
        print "Hostname: " + self.hostname
        print "Username: " + self.username
        print self.connection_string



        if ('-pw' not in connection_string) and password:
            self.connection_string = [r'-pw', password, connection_string]
        else:
            self.connection_string = [connection_string]

        if private_key:
            self.connection_string = ['-i', private_key] + self.connection_string

        if port:
            self.connection_string = ['-P', port] + self.connection_string

        self.idle_recursive = idle_recursive

        self.results = {}
        self.transport = None
        self.sftp = None

        self.results_lock = threading.Condition()
        self.command_deque = deque()

        self.add_command('cd',search_path, True)

        threading.Thread.__init__(self)

    def is_os_mode(self, mode):
        return self.os_mode == mode

    def connect(self):
        if not self.is_os_mode('posix'):
            if not self.sftp:
                self.sftp = psftp(self.connection_string)
                self.sftp.next()
            return self
        else:
            try:
                host_keys = paramiko.util.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
            except IOError:
                try:
                    # try ~/ssh/ too, because windows can't have a folder named ~/.ssh/
                    host_keys = paramiko.util.load_host_keys(os.path.expanduser('~/ssh/known_hosts'))
                except IOError:
                    print '*** Unable to open host keys file'
                    host_keys = {}

            if host_keys.has_key(self.hostname):
                hostkeytype = host_keys[self.hostname].keys()[0]
                hostkey = host_keys[self.hostname][hostkeytype]
                print 'Using host key of type %s' % hostkeytype
            try:
                self.transport = t = paramiko.Transport((self.hostname, 22))
                t.connect(username=self.username, password=self.password, hostkey=hostkey)
                self.sftp = paramiko.SFTPClient.from_transport(t)
                print "SFTP INIT: "+ str(self.transport.is_active())
                self.add_command('cd',self.search_path, True)
            except Exception:
                print "transport Failed"
            return self
            

    def disconnect(self):
        self.add_command('exit','')
        return self

    def add_command(self, command, path, show=False):
        self.results_lock.acquire()
        self.results_lock.notify()
        if show:
            self.show_panel_after = True
        self.command_deque.append((command,path))
        self.results_lock.release()

    def get_front_command(self):

        if len(self.command_deque) > 0:
            return self.command_deque.pop()
        else:
            return (None,None)

    def send_cmd(self, command, path, show_panel):
        print "Command: " + command
        print "Path: " + path
        if command == 'ls':
            if show_panel == True:
                sublime.set_timeout(lambda:sublime.status_message('Opening %s' % path),0)
                self.ls(path)
            if show_panel == True:
                self.showfilepanel()
                sublime.set_timeout(lambda:sublime.status_message('Finished opening %s' % path),0)
        elif command == 'open':
            sublime.set_timeout(lambda:sublime.status_message('Downloading %s' % path),0)
            self.download(path)
            sublime.set_timeout(lambda:sublime.status_message('Finished downloading %s' % path),0)
        elif command == 'save':
            sublime.set_timeout(lambda:sublime.status_message('Uploading %s' % path),0)
            self.upload(path)
            sublime.set_timeout(lambda:sublime.status_message('Finished uploading %s' % path),0)
        elif command == 'cd':
            self.cd(path, show_panel)


    def cd(self, path, show_panel):
        if not self.is_os_mode('posix'):
            self.sftp.send('cd "%s"' % (path) )
            self.add_command('ls','', show_panel)
        else:
            print "changing dir: " + path
            print self.sftp.getcwd()
            self.sftp.chdir(path)
            self.search_path = self.sftp.getcwd()
            self.add_command('ls',path, show_panel)


    def run(self):
        sublime.set_timeout(lambda:sublime.status_message('Connecting to %s' % self.server),0)
        self.connect()
        while True:

            self.results_lock.acquire()
            if len(self.command_deque) == 0:
                self.results_lock.wait()
            show_panel = self.show_panel_after
            if show_panel == True:
                self.show_panel_after = False
            command, path = self.get_front_command()
            self.results_lock.release()

            print command, path, show_panel

            self.send_cmd(command, path, show_panel)

            if command == 'exit':
                break
            else:
                pass


        sublime.set_timeout(lambda:sublime.status_message('Disconnecting from %s' % self.server),0)
        try:
            if not self.is_os_mode('posix'):
                self.sftp.send('exit')
            else:
                self.sftp.close()
                print self.transport.is_active()
                self.transport.close()
                print self.transport.is_active()
                print self.transport.stop_thread()
                self.sftp = None
                self._Thread__stop()
                print threading.enumerate()
                #if os.path.exists(os.path.join(sublime.packages_path(),'Mote','temp',self.server)):
                    #print os.path.join(sublime.packages_path(),'Mote','temp',self.server)
                    #self.rm_rf(str(os.path.join(sublime.packages_path(),'Mote','temp',self.server)))

        except StopIteration:
            pass

        threading.Thread.__init__(self)
        
    def ls(self, search_path = ''):
        fullpath = cleanpath(self.search_path,search_path)
        if not self.is_os_mode('posix'):
            results = self.sftp.send('ls "%s"' % fullpath)
            results = self.cleanls(fullpath, results)
            self.results.update(results)
        else:
            file_list = {}
            file_list = dict(zip(self.sftp.listdir(self.sftp.getcwd()), self.sftp.listdir_attr(self.sftp.getcwd())))
            #results = self.cleanls(fullpath, results)
            results = self.cleanlsposix(fullpath, file_list)
            self.results = results

        if self.idle_recursive:
            subfolders = dict((k,v) for k,v in results.items() if v['type'] == 'folder')
            for recur_folder in subfolders:
                self.add_command('ls',results[recur_folder]['path'])

    def download(self, path):
        if not self.is_os_mode('posix'):
            localpath = os.path.normpath(os.path.join(sublime.packages_path(),'Mote','temp',self.server,path))
        else:
            localpath = os.path.normpath(os.path.join(sublime.packages_path(),'Mote','temp',self.server,path[1:]))

        if not os.path.exists(os.path.dirname(localpath)):
            os.makedirs(os.path.dirname(localpath))

        if not self.is_os_mode('posix'):
            self.sftp.send('get "%s" "%s"' % (path,localpath) )
        else:
            print "preget: "+ path+" "+localpath
            self.sftp.get(path, localpath)

        sublime.set_timeout(lambda:self.window.open_file(localpath), 0)


        pass

    def upload(self, path):
        localpath = os.path.normpath(os.path.join(sublime.packages_path(),'Mote','temp',self.server,path))
        if not self.is_os_mode('posix'):
            self.sftp.send('put "%s" "%s"' % (localpath,path) )
        else:
            self.sftp.put(localpath, '/'+path)

    def showfilepanel(self):
        self.keys = sorted(self.results.keys())
        def show_quick_panel():
            self.window.show_quick_panel(self.keys, self.on_select)
        sublime.set_timeout(show_quick_panel, 10)

    def cleanlsposix(self, fullpath, file_list):
        paths = {}
        paths['..'] = {}
        paths['..']['path'] = '/'.join(self.sftp.getcwd().split('/')[0:-1])
        paths['..']['type'] = 'folder'
        for path, attr in file_list.items():
            dflag = oct(attr.st_mode)
            named_path = cleanpath(fullpath, path)
            if str(dflag[0:2]) == '04':
                path_key = named_path + '/..'
            else:
                path_key = named_path + '-'

            paths[path_key] = {}
            paths[path_key]['path'] = named_path
            if str(dflag[0:2]) == '04':
                paths[path_key]['type'] = 'folder'
            else:
                paths[path_key]['type'] = 'file'
        return paths

    def cleanls(self,fullpath, out):
        paths = {}
        for path in out.split('\n')[2:-1]:
            raw_path = path.rsplit(' ', 1)[-1].strip()
            if raw_path[0] == '.':
                continue

            named_path = cleanpath(fullpath,raw_path)
            path_key = named_path + ('' if path[0] == '-' else '/..')
            print named_path+" " +path_key + " "+path[0]

            #print named_path
            paths[path_key] = {}
            paths[path_key]['path'] = named_path
            paths[path_key]['type'] = 'file' if path[0] == '-' else 'folder'
        #print paths
        return paths

    def on_select(self, picked):
        if picked == -1:
            return
        if not self.results:
            return

        key = self.keys[picked]

        if self.results[key]['type'] == 'folder':
            if not self.is_os_mode('posix'):
                self.add_command('ls',self.results[key]['path'], True)
            else:
                self.add_command('cd',self.results[key]['path'], True)
        elif self.results[key]['type'] == 'file':
            self.add_command('open',self.results[key]['path'])

    def rm_rf(dir):
        for path in (os.path.join(d,f) for f in os.listdir(d)):
            if os.path.isdir(path):
                rm_rf(path)
            else:
                os.unlink(path)
        os.rmdir(d)


def cleanpath(*args):
    return posixpath.normpath(posixpath.join(*args))

def psftp(connection_string):
    command = ''
    exe = [os.path.join(sublime.packages_path(),'Mote','psftp.exe')] + connection_string
    print exe
    p = subprocess.Popen(exe, shell=True, bufsize=1024, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
    while True:
        try:
            command = (yield untilprompt(p,command))
        except Exception as e:
            print e
            return
        #print command
        if command == 'exit':
            untilprompt(p,'exit')
            return

def untilprompt(proc, strinput = None):
    if strinput:
        proc.stdin.write(strinput+'\n')
        proc.stdin.flush()
    buff = ''
    while proc.poll() == None:

        output = proc.stdout.read(1)
        buff += output

        if buff[-7:-1] == 'psftp>':
            break
    return buff

MOTES = main()
