from collections import defaultdict
import os

from dotenv import load_dotenv
import supervisely as sly
import supervisely.io.env as env

if sly.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))

api = sly.Api()

TEAM_ID = env.team_id()
WORKSPACE_ID = env.workspace_id()

src_projects_data = defaultdict(dict)

max_frames = 0


project_id = sly.env.project_id()
dataset_id = 71201
project_meta = sly.ProjectMeta.from_json(data=api.project.get_meta(id=project_id))

data_dir = sly.app.get_data_dir()