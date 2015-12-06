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
        if entity.get('entityType') == 'task' and entity['action'] == 'add':
            task = None
            try:
                task = ftrack.Task(id=entity.get('entityId'))
            except:
                return

            parent = task.getParent()
            if parent.get('thumbid') and not task.get('thumbid'):
                task.set('thumbid', value=parent.get('thumbid'))
                print 'Updated thumbnail on {0!s}/{1!s}'.format(parent.getName(),
                                                        task.getName())


# Subscribe to events with the update topic.
ftrack.setup()
ftrack.EVENT_HUB.subscribe('topic=ftrack.update', callback)
ftrack.EVENT_HUB.wait()
