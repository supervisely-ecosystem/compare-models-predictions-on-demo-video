import os
from shutil import rmtree

from dotenv import load_dotenv
import supervisely as sly


load_dotenv("local.env")
load_dotenv(".env")
load_dotenv(os.path.expanduser("~/supervisely/.env"))

api = sly.Api.from_env()

FRAME_RATE = os.environ["FRAME_RATE"]
workspace_id = os.environ["WORKSPACE_ID"]

workspace = api.workspace.get_info_by_id(workspace_id)
if workspace is None:
    print("you should put correct workspaceId value to local.env")
    raise ValueError(f"Workspace with id={workspace_id} not found")

project = api.project.create(
    workspace_id, "compare predictions", sly.ProjectType.VIDEOS, change_name_if_conflict=True
)

# create temp dir (it will be deleted in the end)
###############################################################
ROOT_PATH = "./src/"
if "temp_data" in os.listdir(ROOT_PATH):
    rmtree(ROOT_PATH + "temp_data")

os.mkdir(ROOT_PATH + "temp_data")
TEMP_PATH = os.path.join(ROOT_PATH, "temp_data/")

os.mkdir(TEMP_PATH + "source")
SOURCE_PATH = os.path.join(TEMP_PATH, "source/")
###############################################################
