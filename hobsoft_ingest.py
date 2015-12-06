import sys
import os

path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ftrack-api')
sys.path.append(path)

import ftrack
import utils


def callback(event):
    """ This plugin sets the task status from the version status update.
    """

    if '7bbf1c8a-b5f5-11e4-980e-040112b6a801' not in event['data']['parents']:
        return

    for entity in event['data'].get('entities', []):

        # Filter non-assetversions
        if entity.get('entityType') == 'assetversion' and entity['action'] == 'update':
            version = ftrack.AssetVersion(id=entity.get('entityId'))
            asset = version.getAsset()

            if version.getVersion() != 1 or asset.getName() != 'hobsoft':
                return

            shot = asset.getParent()
            task = None
            if shot.getTasks(taskTypes=['painting']):
                task = shot.getTasks(taskTypes=['painting'])[0]
            else:
                task_type = utils.GetTaskTypeByName('painting')
                status = utils.GetStatusByName('ready')
                task = shot.createTask('painting', taskType=task_type,
                                        taskStatus=status)
            print 'hobsoft ingest on {0!s}'.format(task)


# Subscribe to events with the update topic.
ftrack.setup()
ftrack.EVENT_HUB.subscribe('topic=ftrack.update', callback)
ftrack.EVENT_HUB.wait()
