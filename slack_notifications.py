import sys
import os
import json

path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ftrack-api')
sys.path.append(path)

import ftrack
from slacker import Slacker

json_file = os.path.join(os.path.dirname(__file__), 'config.json')
config = None
with open(json_file) as json_data:
    config = json.load(json_data)


def callback(event):
    '''Event callback printing all new or updated entities.'''

    # only EAE project
    if '7bbf1c8a-b5f5-11e4-980e-040112b6a801' not in event['data']['parents']:
        return

    slack = Slacker(config['slack_api_token'])

    for entity in event['data'].get('entities', []):

        # Filter non-assetversions
        if entity.get('entityType') == 'task' and entity['action'] == 'update':

            # Find task if it exists
            task = None
            try:
                task = ftrack.Task(id=entity.get('entityId'))
            except:
                return

            if task.getName().lower() != 'compositing':
                return
            if task.get('objecttypename') != 'Task':
                return
            if task.getStatus().get('name').lower() != 'ready':
                return

            # creating channel
            channel = task.getParents()[-1].getName()
            try:
                slack.channels.create(channel)
            except:
                pass

            # posting message
            msg = task.getURL() + ' status update to '
            msg += '"{0}"'.format(task.getStatus().get('name'))
            slack.chat.post_message('#' + channel, msg)


# Subscribe to events with the update topic.
ftrack.setup()
ftrack.EVENT_HUB.subscribe('topic=ftrack.update', callback)
ftrack.EVENT_HUB.wait()
