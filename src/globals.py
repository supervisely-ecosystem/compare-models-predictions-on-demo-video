import os

from dotenv import load_dotenv
import supervisely as sly

if sly.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))


api = sly.Api.from_env()

workspace_id = os.environ["WORKSPACE_ID"]

workspace = api.workspace.get_info_by_id(workspace_id)
if workspace is None:
    print("you should put correct workspaceId value to local.env")
    raise ValueError(f"Workspace with id={workspace_id} not found")

project = api.project.create(
    workspace_id, "compare predictions", sly.ProjectType.VIDEOS, change_name_if_conflict=True
)
