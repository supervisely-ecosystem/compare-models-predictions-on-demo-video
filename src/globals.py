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
