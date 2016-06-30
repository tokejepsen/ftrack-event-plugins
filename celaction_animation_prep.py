import sys
import os
import platform
import shutil
import logging

logging.basicConfig()

path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ftrack-api')
sys.path.append(path)

import ftrack
import ftrack_api


def GetTaskFilename(task_id, ext):

    session = ftrack_api.Session()
    task = session.query('Task where id is "%s"' % task_id).one()
    path = []
    parents = task['link']
    project = session.query('Project where id is "%s"' % parents[0]['id'])

    disk = project.one()['disk']['windows']
    if platform.system().lower() != 'windows':
        disk = project.one()['disk']['unix']
    path.append(disk)

    path.append(project.one()['root'])

    root_folder = []
    for p in parents[1:]:
        tc = session.query('TypedContext where id is "%s"' % p['id']).one()
        path.append(tc['name'].lower())

        if tc['object_type']['name'] == 'Episode':
            root_folder.append('episodes')
        if tc['object_type']['name'] == 'Sequence':
            root_folder.append('sequences')
        if tc['object_type']['name'] == 'Shot':
            root_folder.append('shots')
    root_folder.append('tasks')
    path.insert(2, root_folder[0])

    filename = [parents[-2]['name'], parents[-1]['name'], 'v001', ext]
    path.append('.'.join(filename))

    return os.path.join(*path).replace('\\', '/')


def callback(event):
    """ This plugin copies the layout celaction scene file, if no version is
        present, and when the animation task status changes to 'ready'
    """
    # exclusive to tog project
    if '20010154-1c3f-11e6-89ac-42010af00048' not in event['data']['parents']:
        return

    for entity in event['data'].get('entities', []):
        if entity.get('entityType') == 'task' and entity['action'] == 'update':
            task = None
            try:
                task = ftrack.Task(id=entity.get('entityId'))
            except:
                return

            # filter to "ready" tasks only
            if task.getStatus().getName().lower() != 'ready':
                return

            # filter to animation tasks only
            if task.getType().getName().lower() != 'animation':
                return

            # check if any scene component exists
            for v in task.getAssetVersions():
                try:
                    if v.getComponent(name='celaction_publish'):
                        return
                except:
                    pass

            # get latest layout version with a celaction_publish component
            layout_task = None
            if task.getParent().getTasks(taskTypes=['Layout']):
                tasks = task.getParent().getTasks(taskTypes=['Layout'])
                layout_task = tasks[0]
            else:
                return
            component = None
            for asset in layout_task.getAssets(assetTypes=['scene']):
                v = asset.getVersions(componentNames=['celaction_publish'])
                if v:
                    component = v[-1].getComponent(name='celaction_publish')

            # copy layout file to work area
            src = component.getFilesystemPath()
            work_file = GetTaskFilename(task.getId(), 'scn')
            if not os.path.exists(os.path.dirname(work_file)):
                os.makedirs(os.path.dirname(work_file))
            if not os.path.exists(work_file):
                shutil.copy(src, work_file)

            # copy layout file to publish area
            src = component.getFilesystemPath()
            publish_file = os.path.dirname(work_file)
            publish_file = os.path.join(publish_file, 'publish',
                                        os.path.basename(work_file))
            if not os.path.exists(os.path.dirname(publish_file)):
                os.makedirs(os.path.dirname(publish_file))
            if not os.path.exists(publish_file):
                shutil.copy(src, publish_file)

            # create and publish version
            parent = task.getParent()
            asset = parent.createAsset(name='animation', assetType='scene')
            version = asset.createVersion(comment='Auto publish from Layout',
                                          taskid=task.getId())
            version.createComponent(name='celaction_work', path=work_file)
            version.createComponent(name='celaction_publish',
                                    path=publish_file)
            version.publish()

# Subscribe to events with the update topic.
ftrack.setup()
ftrack.EVENT_HUB.subscribe('topic=ftrack.update', callback)
ftrack.EVENT_HUB.wait()
