import os
import tempfile
import subprocess
import operator
import sys

path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ftrack-api')
sys.path.append(path)

import ftrack


def GetAssetNameById(id):
    for t in ftrack.getAssetTypes():
        try:
            if t.get('typeid') == id:
                return t.get('name')
        except:
            return None

def GetTaskTypeByName(name):
    task_types = ftrack.getTaskTypes()

    result = None
    for s in task_types:
        if s.getName().lower() == name.lower():
            result = s

    return result

def GetStatusByName(name):
    statuses = ftrack.getTaskStatuses()

    result = None
    for s in statuses:
        if s.get('name').lower() == name.lower():
            result = s

    return result


def GetNextTask(task):
    shot = task.getParent()
    tasks = shot.getTasks()

    def sort_types(types):
        data = {}
        for t in types:
            data[t] = t.get('sort')

        data = sorted(data.items(), key=operator.itemgetter(1))
        results = []
        for item in data:
            results.append(item[0])

        return results

    types_sorted = sort_types(ftrack.getTaskTypes())

    next_types = None
    for t in types_sorted:
        if t.get('typeid') == task.get('typeid'):
            try:
                next_types = types_sorted[(types_sorted.index(t) + 1):]
            except:
                pass

    for nt in next_types:
        for t in tasks:
            if nt.get('typeid') == t.get('typeid'):
                return t

    return None

def getLatestVersion(versions):
    latestVersion = None
    if len(versions) > 0:
        versionNumber = 0
        for item in versions:
            if item.get('version') > versionNumber:
                versionNumber = item.getVersion()
                latestVersion = item
    return latestVersion

def getShots(entity):
    result = []

    if entity.get('objecttypename') == 'Task':
        for parent in entity.getParents():
            try:
                if parent.get('objecttypename') == 'Shot':
                    result.append(parent)
            except:
                pass

    if entity.get('objecttypename') == 'Shot':
        result.append(entity)

    if entity.get('objecttypename') == 'Sequence':
        for shot in entity.getShots():
            result.extend(getShots(shot))

    if entity.get('objecttypename') == 'Episode':
        for seq in entity.getSequences():
            result.extend(getShots(seq))

    return result

def getThumbnailRecursive(task):
    if task.get('thumbid'):
        thumbid = task.get('thumbid')
        return ftrack.Attachment(id=thumbid)
    if not task.get('thumbid'):
        parent = ftrack.Task(id=task.get('parent_id'))
        return getThumbnailRecursive(parent)

def getTasksRecursive(entity):
    result = []

    if entity.get('objecttypename') == 'Task':
        result.append(entity)

    if entity.get('objecttypename') == 'Shot':
        for task in entity.getTasks():

            result.append(task)

    if entity.get('objecttypename') == 'Sequence':
        for shot in entity.getShots():
            result.extend(getTasksRecursive(shot))

    if entity.get('objecttypename') == 'Episode':
        for seq in entity.getSequences():
            result.extend(getTasksRecursive(seq))

    return result
