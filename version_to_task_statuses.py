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
        if entity.get('entityType') == 'assetversion' and entity['action'] == 'update':
            version = ftrack.AssetVersion(id=entity.get('entityId'))
            version_status = version.getStatus()
            try:
                task = ftrack.Task(version.get('taskid'))
            except:
                return

            task_status = utils.GetStatusByName(version_status.get('name').lower())

            # Filter to versions with status change to "render complete"
            if version_status.get('name').lower() == 'render complete':

                task_status = utils.GetStatusByName('artist review')

            # Proceed if the task status was set
            if task_status:

                # Get path to task
                path = task.get('name')
                for p in task.getParents():
                    path = p.get('name') + '/' + path

                # Setting task status
                try:
                    task.setStatus(task_status)
                except Exception as e:
                    print '%s status couldnt be set: %s' % (path, e)
                else:
                    print '%s updated to "%s"' % (path, task_status.get('name'))


# Subscribe to events with the update topic.
ftrack.setup()
ftrack.EVENT_HUB.subscribe('topic=ftrack.update', callback)
ftrack.EVENT_HUB.wait()
