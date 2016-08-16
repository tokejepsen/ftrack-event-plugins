import sys
import os

func = os.path.dirname
path = os.path.join(func(func(__file__)), "ftrack-api")
sys.path.append(path)
path = os.path.join(func(func(func(__file__))), "pipeline-schema")
sys.path.append(path)

import ftrack
import pipeline_schema


def callback(event):
    """ This plugin sets the task status from the version status update.
    """

    for entity in event["data"].get("entities", []):

        # Filter non-assetversions
        if (entity.get("entityType") == "task" and
           entity["action"] in ["add", "move"]):

            data = pipeline_schema.get_data(entity.get("entityId"))
            data["extension"] = "temp"
            path = pipeline_schema.get_path("task_work", data)

            # create source folder
            src_dir = os.path.join(os.path.dirname(path), "source")
            if not os.path.exists(src_dir):
                os.makedirs(src_dir)
                print "Creating folder: %s" % src_dir


# Subscribe to events with the update topic.
ftrack.setup()
ftrack.EVENT_HUB.subscribe("topic=ftrack.update", callback)
ftrack.EVENT_HUB.wait()
