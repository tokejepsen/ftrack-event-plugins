import sys
import os
import tempfile
import subprocess
import re

path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ftrack-api')
sys.path.append(path)

import ftrack


def CallDeadlineCommand(arguments, hideWindow=True):
    # On OSX, we look for the DEADLINE_PATH file. On other platforms,
    # we use the environment variable.
    if os.path.exists("/Users/Shared/Thinkbox/DEADLINE_PATH"):
        with open("/Users/Shared/Thinkbox/DEADLINE_PATH") as f:
            deadlineBin = f.read().strip()
        deadlineCommand = deadlineBin + "/deadlinecommand"
    else:
        deadlineBin = os.environ['DEADLINE_PATH']
        if os.name == 'nt':
            deadlineCommand = deadlineBin + "\\deadlinecommand.exe"
        else:
            deadlineCommand = deadlineBin + "/deadlinecommand"

    startupinfo = None
    if hideWindow and os.name == 'nt' and hasattr(subprocess,
                                                  'STARTF_USESHOWWINDOW'):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    environment = {}
    for key in os.environ.keys():
        environment[key] = str(os.environ[key])

    # Need to set the PATH, cuz windows seems to load DLLs
    # from the PATH earlier that cwd....
    if os.name == 'nt':
        path = str(deadlineBin + os.pathsep + os.environ['PATH'])
        environment['PATH'] = path

    arguments.insert(0, deadlineCommand)

    # Specifying PIPE for all handles to workaround a Python bug on Windows.
    # The unused handles are then closed immediatley afterwards.
    proc = subprocess.Popen(arguments, cwd=deadlineBin,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, startupinfo=startupinfo,
                            env=environment)
    proc.stdin.close()
    proc.stderr.close()

    output = proc.stdout.read()

    return output


def callback(event):
    """ This plugin sets the task status from the version status update.
    """

    if '7bbf1c8a-b5f5-11e4-980e-040112b6a801' not in event['data']['parents']:
        return

    for entity in event['data'].get('entities', []):

        # Filter non-assetversions
        if entity.get('entityType') == 'task' and entity['action'] == 'update':

            # Find task if it exists
            task = None
            try:
                task = ftrack.Task(id=entity.get('entityId'))
            except:
                return

            # Filter to tasks with complete status
            if task.get('objecttypename') != 'Task':
                return

            status = task.getStatus().get('name').lower()
            if status not in ['wip', 'proposed final']:
                return

            if task.getName().lower() != 'compositing':
                return

            version = task.getParent().getAsset('compositing', 'img')
            version = version.getVersions()[-1]
            src = version.getComponent().getFilesystemPath()
            src = src.replace('%04d', '####')

            sequence_name = task.getParent().getParent().getName()
            shot_name = 'c' + task.getParent().getName().split('c')[1]
            filename = '%s%s_compositing.####.dpx' % (sequence_name,
                                                      shot_name)
            dst = os.path.join('B:\\', 'film', sequence_name, shot_name,
                               'current', 'compositing', filename.upper())

            if not os.path.exists(os.path.dirname(dst)):
                os.makedirs(os.path.dirname(dst))

            for f in os.listdir(os.path.dirname(dst)):
                try:
                    p = os.path.join(os.path.dirname(dst), f)
                    os.remove(p)
                except:
                    pass

            script = os.path.join(os.path.dirname(__file__), 'draft',
                                  'exr_to_dpx_cineon.py')

            frame_start = int(task.getParent().get('fstart'))
            frame_end = int(task.getParent().get('fend'))

            path = task.getParent().getName() + '/'
            path += version.getAsset().getName() + ' '
            path += 'v%s' % str(version.getVersion()).zfill(2)

            # job data
            data = 'UserName=render.farm\n'
            data += 'Name=%s Transcoding\n' % path
            data += 'Frames=%s-%s\n' % (frame_start, frame_end)
            data += 'Group=draft\n'
            data += 'Pool=medium\n'
            data += 'Plugin=Draft\n'
            data += 'LimitGroups=draft\n'
            data += 'ChunkSize=5\n'

            current_dir = tempfile.gettempdir()
            filename = 'job.txt'
            job_path = os.path.join(current_dir, filename)

            with open(job_path, 'w') as outfile:
                outfile.write(data)

            # plugin data
            data = 'scriptFile=%s\n' % script
            data += 'ScriptArg0=frameList=%s-%s\n' % (frame_start, frame_end)
            data += 'ScriptArg1=outFile=%s\n' % dst
            data += 'ScriptArg2=inFile=%s\n' % src

            current_dir = tempfile.gettempdir()
            filename = 'plugin.txt'
            plugin_path = os.path.join(current_dir, filename)

            with open(plugin_path, 'w') as outfile:
                outfile.write(data)

            # submitting job
            args = [job_path, plugin_path]

            result = CallDeadlineCommand(args)

            job_id = re.search(r'JobID=(.*)', result).groups()[0]

            # deleting temporary files
            os.remove(job_path)
            os.remove(plugin_path)

            # creating dependent job
            data = 'UserName=render.farm\n'
            data += 'Name=%s Transcoding\n' % path
            data += 'Frames=%s-%s\n' % (frame_start, frame_end)
            data += 'Group=image_magick\n'
            data += 'Pool=medium\n'
            data += 'Plugin=CommandLine\n'
            data += 'ChunkSize=5\n'
            data += 'JobDependencies=%s\n' % job_id

            current_dir = tempfile.gettempdir()
            filename = 'job.txt'
            job_path = os.path.join(current_dir, filename)

            with open(job_path, 'w') as outfile:
                outfile.write(data)

            # plugin data
            path = dst.replace('####', '%04d') + '[<STARTFRAME>-<ENDFRAME>]'
            args = '{0} -scene <STARTFRAME> -depth 10 '.format(path)
            args += '-define dpx:television.time.code=00:00:00:01 '
            args += '-type TrueColor'
            data = 'Arguments={0} {1}\n'.format(args, path)
            path = r'K:\development\tools\image-magick\convert.exe'
            data += 'Executable={0}'.format(path)

            current_dir = tempfile.gettempdir()
            filename = 'plugin.txt'
            plugin_path = os.path.join(current_dir, filename)

            with open(plugin_path, 'w') as outfile:
                outfile.write(data)

            # submitting job
            args = [job_path, plugin_path]

            print CallDeadlineCommand(args)

            # deleting temporary files
            os.remove(job_path)
            os.remove(plugin_path)

# Subscribe to events with the update topic.
ftrack.setup()
ftrack.EVENT_HUB.subscribe('topic=ftrack.update', callback)
ftrack.EVENT_HUB.wait()
