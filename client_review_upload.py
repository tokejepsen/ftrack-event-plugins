import sys
import os
import threading

path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ftrack-api')
sys.path.append(path)

import ftrack
import utils

class Thread(threading.Thread):

    def __init__(self, version, path, log):
        threading.Thread.__init__(self)
        self.version = version
        self.path = path
        self.log = log

    def run(self):

        ftrack.Review.makeReviewable(self.version, self.path)
        print 'uploaded: %s' % self.path
        self.version.publish()

def callback(event):
    """ This plugin sets the task status from the version status update.
    """

    for entity in event['data'].get('entities', []):
        if entity.get('entityType') == 'reviewsessionobject' and entity['action'] == 'add':
            version = None
            try:
                version = ftrack.AssetVersion(entity['changes']['version_id']['new'])
            except:
                return

            user = ftrack.User(event['source']['user']['id'])
            os.environ['LOGNAME'] = user.getUsername()

            path = version.getComponent().getFilesystemPath()
            myclass = Thread(version, path, log)
            myclass.start()

# Subscribe to events with the update topic.
ftrack.setup()
ftrack.EVENT_HUB.subscribe('topic=ftrack.update', callback)
ftrack.EVENT_HUB.wait()
