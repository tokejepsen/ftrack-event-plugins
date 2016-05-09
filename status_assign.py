import sys
import os

path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ftrack-api')
sys.path.append(path)

import ftrack


def callback(event):
    """ This plugin sets the task status from the version status update.
    """

    for entity in event['data'].get('entities', []):

        # Filter non-assetversions
        if entity.get('entityType') == 'task' and entity['action'] == 'update':

            if 'statusid' not in entity.get('keys'):
                return

            # Find task if it exists
            task = None
            try:
                task = ftrack.Task(id=entity.get('entityId'))
            except:
                return

            # remove status assigned users
            if task.getMeta('assignees'):
                for userid in task.getMeta('assignees').split(','):
                    try:
                        task.unAssignUser(ftrack.User(userid))
                    except:
                        pass

            # getting status named group
            task_status_name = task.getStatus().get('name').lower()

            project = task.getParents()[-1]
            status_group = None
            for group in project.getAllocatedGroups():
                if group.getSubgroups():
                    if group.get('name').lower() == task_status_name:
                        status_group = group

            users = []
            if status_group:

                for group in status_group.getSubgroups():
                    task_type_name = task.getType().get('name').lower()
                    if task_type_name == group.get('name').lower():

                        # assigning new users
                        for member in group.getMembers():
                            try:
                                task.assignUser(member)
                                users.append(member.get('userid'))
                            except:
                                pass

            # storing new assignees
            value = ''
            for user in users:
                value += user + ','
            try:
                value = value[:-1]
            except:
                pass
            task.setMeta('assignees', value=value)


# Subscribe to events with the update topic.
ftrack.setup()
ftrack.EVENT_HUB.subscribe('topic=ftrack.update', callback)
ftrack.EVENT_HUB.wait()
