import os
from dotenv import load_dotenv
import supervisely as sly



if sly.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))
