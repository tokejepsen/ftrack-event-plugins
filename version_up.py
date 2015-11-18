import os
import re
import shutil
import traceback
import sys

path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ftrack-api')
sys.path.append(path)

import ftrack
import utils


def version_get(string, prefix, suffix = None):
  """Extract version information from filenames used by DD (and Weta, apparently)
  These are _v# or /v# or .v# where v is a prefix string, in our case
  we use "v" for render version and "c" for camera track version.
  See the version.py and camera.py plugins for usage."""

  if string is None:
    raise ValueError, "Empty version string - no match"

  regex = "[/_.]"+prefix+"\d+"
  matches = re.findall(regex, string, re.IGNORECASE)
  if not len(matches):
    msg = "No \"_"+prefix+"#\" found in \""+string+"\""
    raise ValueError, msg
  return (matches[-1:][0][1], re.search("\d+", matches[-1:][0]).group())


def version_set(string, prefix, oldintval, newintval):
  """Changes version information from filenames used by DD (and Weta, apparently)
  These are _v# or /v# or .v# where v is a prefix string, in our case
  we use "v" for render version and "c" for camera track version.
  See the version.py and camera.py plugins for usage."""

  regex = "[/_.]"+prefix+"\d+"
  matches = re.findall(regex, string, re.IGNORECASE)
  if not len(matches):
    return ""

  # Filter to retain only version strings with matching numbers
  matches = filter(lambda s: int(s[2:]) == oldintval, matches)

  # Replace all version strings with matching numbers
  for match in matches:
    # use expression instead of expr so 0 prefix does not make octal
    fmt = "%%(#)0%dd" % (len(match) - 2)
    newfullvalue = match[0] + prefix + str(fmt % {"#": newintval})
    string = re.sub(match, newfullvalue, string)
  return string

def get_version_up(path):
    (prefix, v) = version_get(path, 'v')
    v = int(v)
    return version_set(path, prefix, v, v + 1)

def version_up(path):
    new_path = get_version_up(path)

    if not os.path.exists(os.path.dirname(new_path)):
        os.makedirs(os.path.dirname(new_path))

    if not os.path.exists(new_path):
        print 'Copying: %s' % path
        shutil.copy(path, new_path)

    (prefix, v) = version_get(path, 'v')
    v = int(v)

    return [new_path, v + 1]


def callback(event):
    """ This plugin sets the task status from the version status update.
    """

    for entity in event['data'].get('entities', []):

        # Filter non-assetversions
        if entity.get('entityType') == 'task' and entity['action'] == 'update':

            # Find task if it exists
            task = None
            try:
                task = ftrack.Task(id=entity.get('entityId'))
            except:
                return

            # Filter to tasks with "pending changes" status
            status_check = False
            if task and task.get('objecttypename') == 'Task':
                if task.getStatus().get('name').lower() == 'pending changes':
                    status_check = True

            # check that its an compositing task
            comp_check = False
            if status_check:
                for t in ftrack.getTaskTypes():
                    if task.get('typeid') == t.get('typeid'):
                        if t.get('name').lower() == 'compositing':
                            comp_check = True

            scene_asset = None
            if status_check:
                try:
                    for a in task.getAssets(assetTypes=['scene']):
                        if task.getName() == a.getName():
                            scene_asset = a
                except:
                    pass

            if scene_asset:
                version_copy = False

                try:
                    for version in scene_asset.getVersions():

                        for c in version.getComponents():
                            if c.getName().endswith('_work'):

                                # version up scene file
                                path = c.getFilesystemPath()
                                prefix = os.path.basename(path).split('v')[0]
                                extension = os.path.splitext(path)[1]
                                max_version = int(version_get(path, 'v')[1])

                                for f in os.listdir(os.path.dirname(path)):
                                    basename = os.path.basename(f)
                                    f_prefix = os.path.basename(basename).split('v')[0]
                                    if f_prefix == prefix and basename.endswith(extension):
                                        if int(version_get(f, 'v')[1]) > max_version:
                                            max_version = int(version_get(f, 'v')[1])
                                            path = os.path.dirname(path)
                                            path = os.path.join(path, basename)

                                version_string = 'v' + str(max_version).zfill(3)
                                ext = os.path.splitext(path)[1]
                                path_dir = os.path.dirname(path)
                                files = []
                                for f in os.listdir(path_dir):
                                    if version_string in f and f.endswith(ext):
                                        files.append(os.path.join(path_dir, f))

                                path = max([f for f in files], key=os.path.getctime)

                                version_number = int(version_get(path, 'v')[1])

                                if int(version_get(path, 'v')[1]) <= version.getVersion():
                                    version_copy = True
                                    if path.split(version_string)[-1] != extension:
                                        [new_path, new_version_number] = version_up(path)
                                        version_string = 'v' + str(new_version_number).zfill(3)
                                        new_name = version_string.join(new_path.split(version_string)[:-1]) + version_string + extension
                                        os.rename(new_path, new_name)
                                        print 'Renaming to %s' % new_name
                                    else:
                                        [new_path, new_version_number] = version_up(path)

                                    path = task.get('name')
                                    for p in task.getParents():
                                        path = p.get('name') + '/' + path

                                    msg = "Version from %s" % int(version_number)
                                    msg += " to %s on %s" % (int(new_version_number), path)
                                    print msg
                except:
                    print traceback.format_exc()


# Subscribe to events with the update topic.
ftrack.setup()
ftrack.EVENT_HUB.subscribe('topic=ftrack.update', callback)
ftrack.EVENT_HUB.wait()
