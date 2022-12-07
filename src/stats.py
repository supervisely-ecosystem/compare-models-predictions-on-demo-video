import os
from shutil import rmtree

from dotenv import load_dotenv
import supervisely as sly

load_dotenv("local.env")
load_dotenv(".env")
load_dotenv(os.path.expanduser("~/supervisely/.env"))

api = sly.Api.from_env()

ROOT_PATH = "./src/temp_data/"
FRAME_RATE = (os.environ["FRAME_RATE"])
workspace_id = os.environ["WORKSPACE_ID"]

workspace = api.workspace.get_info_by_id(workspace_id)
if workspace is None:
    print("you should put correct workspaceId value to local.env")
    raise ValueError(f"Workspace with id={workspace_id} not found")


# get test data
###############################################################
src_project_ids = list(map(int, os.environ["CONTEXT_PROJECTID"].split(",")))
src_datasets = [api.dataset.get_list(id) for id in src_project_ids]
# # ###############################################################
min_frames = 10

# check projects have same count of datasets
len_first = len(src_datasets[0]) if src_datasets else None
same_length = all(len(i) == len_first for i in src_datasets)
if not same_length:
    print("Datasets structure differ")
    raise ValueError("Datasets structure differ")

# create tem dir for dataset images
if "source" in os.listdir(ROOT_PATH):
    rmtree(ROOT_PATH + "source")
if "results" in os.listdir(ROOT_PATH):
    rmtree(ROOT_PATH + "results")

os.mkdir(ROOT_PATH + "source")
os.mkdir(ROOT_PATH + "results")

SOURCE_PATH = os.path.join(ROOT_PATH, "source/")
RESULT_PATH = os.path.join(ROOT_PATH, "results/")
