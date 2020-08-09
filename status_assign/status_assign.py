import ftrack_api


def callback(event):
    session = ftrack_api.Session(auto_connect_event_hub=False)
    for entity_data in event["data"]["entities"]:

        # Filter to tasks.
        if entity_data["entityType"].lower() != "task":
            continue

        if "statusid" not in entity_data["keys"]:
            continue

        task = session.get("Task", entity_data["entityId"])

        if task is None:
            continue

        hierarchy = []
        for item in task['link']:
            hierarchy.append(session.get(item['type'], item['id']))

        hierarchy_path = "/".join([x["name"] for x in hierarchy])

        # Status assignees.
        assignees = []
        if task["metadata"].get("assignees"):
            assignees = [
                session.get("User", userid)
                for userid in task["metadata"]["assignees"].split(",")
            ]

        # Get task users and remove status assigned users.
        task_users = set()
        status_appointments = []
        for appointment in task["appointments"]:
            resource = appointment["resource"]

            # Filter to Users.
            if not isinstance(resource, session.types["User"]):
                continue

            if resource in assignees:
                status_appointments.append(appointment)
                continue

            task_users.add(resource)

        for appointment in status_appointments:
            session.delete(appointment)
            print(
                "Unassigning \"{} {}\" from task \"{}\"".format(
                    appointment["resource"]["first_name"],
                    appointment["resource"]["last_name"],
                    hierarchy_path
                )
            )

        # Getting status members.
        project = session.get(
            "Project", entity_data["parents"][-1]["entityId"]
        )
        status_users = set()
        for allocation in project["allocations"]:
            resource = allocation["resource"]

            # Filter to groups.
            if not isinstance(resource, session.types["Group"]):
                continue

            # Filter to groups named the same as the tasks status.
            if resource["name"].lower() != task["status"]["name"].lower():
                continue

            # Collect all users from status group.
            for membership in resource["memberships"]:
                status_users.add(membership["user"])

            for child in resource["children"]:
                # Filter to groups.
                if not isinstance(child, session.types["Group"]):
                    continue

                # Filter to groups named the same as the tasks type.
                if child["name"].lower() != task["type"]["name"].lower():
                    # Remove users not in task type status.
                    for membership in child["memberships"]:
                        status_users.remove(membership["user"])

        # Assign members to task.
        assigned_users = []
        for user in status_users:
            if user in task_users:
                continue

            session.create(
                "Appointment",
                {
                    "context": task,
                    "resource": user,
                    "type": "assignment"
                }
            )
            assigned_users.append(user)

            print(
                "Assigning \"{} {}\" to task \"{}\"".format(
                    user["first_name"], user["last_name"], hierarchy_path
                )
            )

        # Storing new assignees.
        task["metadata"].update(
            {"assignees": ",".join([user["id"] for user in assigned_users])}
        )

        session.commit()


session = ftrack_api.Session(auto_connect_event_hub=True)
session.event_hub.subscribe("topic=ftrack.update", callback)
session.event_hub.wait()
