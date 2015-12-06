import sys
import os

path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ftrack-api')
sys.path.append(path)

import ftrack
import utils


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

            # Filter to tasks with complete status
            check = False
            if task and task.get('objecttypename') == 'Task':
                if task.getStatus().get('name').lower() == 'supervisor review':
                    check = True


            if check:

                # setting image sequence
                version_number = 0
                version_latest = None
                for version in task.getAssetVersions():
                    if version.getAsset().getType().getShort() == 'img' and \
                    version.getVersion() > version_number:
                        version_number = version.getVersion()
                        version_latest = version

                if version_latest:
                    status = utils.GetStatusByName('supervisor review')
                    version_latest.setStatus(status)

                    path = task.getParent().getName() + '/'
                    path += version_latest.getAsset().getName() + ' '
                    path += 'v{0!s}'.format(str(version_latest.getVersion()).zfill(2))
                    print 'Setting {0!s} "img" to "Supervisor Review"'.format(path)

                # setting movie
                version_number = 0
                version_latest = None
                for version in task.getAssetVersions():
                    if version.getAsset().getType().getShort() == 'mov' and \
                    version.getVersion() > version_number:
                        version_number = version.getVersion()
                        version_latest = version

                if version_latest:
                    status = utils.GetStatusByName('supervisor review')
                    version_latest.setStatus(status)

                    path = task.getParent().getName() + '/'
                    path += version_latest.getAsset().getName() + ' '
                    path += 'v{0!s}'.format(str(version_latest.getVersion()).zfill(2))
                    print 'Setting {0!s} "mov" to "Supervisor Review"'.format(path)


# Subscribe to events with the update topic.
ftrack.setup()
ftrack.EVENT_HUB.subscribe('topic=ftrack.update', callback)
ftrack.EVENT_HUB.wait()
