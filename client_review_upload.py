import sys
import os
import threading
import json
import traceback

path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ftrack-api')
sys.path.append(path)

import ftrack


class Thread(threading.Thread):

    def __init__(self, version, user):
        threading.Thread.__init__(self)
        self.version = version
        self.user = user

    def delete_file(self, name):
        try:
            component = self.version.getComponent(name=name)
            cid = component.getId()
            ftrack.Location('ftrack.server').removeComponent(cid)
        except:
            print traceback.format_exc()
            return
        else:
            self.delete_file(name)

    def delete_component(self, name):
        try:
            component = self.version.getComponent(name=name)
            component.delete()
        except:
            print traceback.format_exc()
            return
        else:
            self.delete_component(name)

    def run(self):

        path = ''
        for p in reversed(self.version.getParents()[:-2]):
            path += p.getName() + '/'
        path += 'v' + str(self.version.getVersion()).zfill(3)
        job = ftrack.createJob('Uploading %s' % path,
                               'running', self.user)

        path = self.version.getComponent().getFilesystemPath()

        self.delete_file('ftrackreview-mp4')
        self.delete_component('ftrackreview-mp4')

        self.delete_file('ftrackreview-webm')
        self.delete_component('ftrackreview-webm')

        try:
            component = self.version.createComponent(
                'ftrackreview-mp4', path=path,
                location=ftrack.Location('ftrack.server'))

            # Meta data needs to contain *frameIn*, *frameOut* and *frameRate*.
            shot = self.version.getAsset().getParent()
            meta_data = json.dumps({'frameIn': int(shot.get('fstart')),
                                    'frameOut': int(shot.get('fend')),
                                    'frameRate': int(shot.get('fps'))})

            component.setMeta(key='ftr_meta', value=meta_data)

            print 'uploaded: %s' % path
        except:
            job.setStatus('failed')

            print traceback.format_exc()
        else:
            job.setStatus('done')
        finally:
            self.version.publish()


def callback(event):
    """ This plugin sets the task status from the version status update.
    """

    for entity in event['data'].get('entities', []):
        if (entity.get('entityType') == 'reviewsessionobject' and
            entity['action'] == 'add'):

            version = None
            try:
                version_id = entity['changes']['version_id']['new']
                version = ftrack.AssetVersion(version_id)
            except:
                return

            user = ftrack.User(event['source']['user']['id'])
            os.environ['LOGNAME'] = user.getUsername()

            myclass = Thread(version, user)
            myclass.start()

# Subscribe to events with the update topic.
ftrack.setup()
ftrack.EVENT_HUB.subscribe('topic=ftrack.update', callback)
ftrack.EVENT_HUB.wait()
