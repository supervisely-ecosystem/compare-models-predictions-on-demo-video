from collections import defaultdict
import os

from dotenv import load_dotenv
import supervisely as sly

if sly.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))

WORKSPACE_ID = os.environ["context.workspaceId"]
label_opacity = int(os.environ["modal.state.opacity"])
border_thickness = int(os.environ["modal.state.thickness"])

api = sly.Api()

workspace = api.workspace.get_info_by_id(WORKSPACE_ID)

if workspace is None:
    print("you should put correct workspaceId value to local.env")
    raise ValueError(f"Workspace with id={WORKSPACE_ID} not found")

TEAM_ID = api.team.get_info_by_id(workspace.team_id)

src_projects_data = defaultdict(dict)
