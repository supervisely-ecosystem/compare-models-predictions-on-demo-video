from collections import defaultdict
import os
from shutil import rmtree

import cv2
from pprint import pprint
import supervisely as sly

import functions as f
import globals as g


project_ids = list(map(int, os.environ["CONTEXT_PROJECTID"].split(",")))
DATA_DIR = sly.app.get_data_dir()
src_projects_data = defaultdict(dict)
correct_datasets = []
result_paths = defaultdict(list)


# collect all projects data
for id in project_ids:
    meta_json = g.api.project.get_meta(id)
    src_projects_data[id]["meta"] = sly.ProjectMeta.from_json(meta_json)

    # get project`s all datasets
    project_datasets = g.api.dataset.get_list(id)
    for ds in project_datasets:

        # get dataset`s all imageInfos
        ds_images = g.api.image.get_list(ds.id)
        images = defaultdict(dict)
        for image in ds_images:
            images[image.name] = image

        src_projects_data[id]["datasets"] = defaultdict()
        ds_data = {"info": ds, "images": images}
        src_projects_data[id]["datasets"][ds.name] = ds_data


# take the first project and check
f_key, f_project = next(iter(src_projects_data.items()))


# check datasets, images and merge images to frames
for ds_name, dataset in f_project["datasets"].items():
    FRAMES_PATH = os.path.join(DATA_DIR, dataset["info"].name)

    if not os.path.exists(FRAMES_PATH):
        os.mkdir(FRAMES_PATH)

    if not all(ds_name in p["datasets"].keys() for p in src_projects_data.values()):
        continue
    for img_name, image_info in dataset["images"].items():
        if not all(
            img_name in p["datasets"][ds_name]["images"].keys() for p in src_projects_data.values()
        ):
            continue
        temp_ann = [] # clean after each frame merging
        TEMP_PATH = os.path.join(FRAMES_PATH, "temp") # clean after each frame merging
        if "temp" not in os.listdir(FRAMES_PATH):
            os.mkdir(TEMP_PATH)

        project_meta = []
        for pid, project in src_projects_data.items():
            image_path = os.path.join(TEMP_PATH, f"{pid}-{image_info.name}")
            img_id = project["datasets"][ds_name]["images"][image_info.name].id

            g.api.image.download_path(img_id, image_path)
            temp_ann.append(g.api.annotation.download(img_id))
            project_meta.append(project["meta"])
            if len(os.listdir(TEMP_PATH)) == len(src_projects_data.values()):
                orig = [cv2.imread(f"{TEMP_PATH}/{path}") for path in os.listdir(TEMP_PATH)]
                cv2.imshow("asdfdsf", orig[0])
                cv2.waitKey(1500)
                cv2.destroyAllWindows()
                images_ann = [
                    sly.Annotation.from_json(temp_ann[i].annotation, project_meta[i])
                    for i in range(len(temp_ann))
                ]
                for i in range(len(orig)):
                    images_ann[i].draw_pretty(orig[i], thickness=3)
                small = [cv2.resize(img, dsize=(0, 0), fx=0.5, fy=0.5) for img in orig]

                grid_size = f.get_grid_size(len(small))
                frame = f.create_image_grid(small, grid_size=grid_size)
                path = os.path.join(FRAMES_PATH, img_name)
                cv2.imwrite(path, frame)
                result_paths[ds_name].append(path)

                rmtree(TEMP_PATH)  # clean temp dir after frame merging
    correct_datasets.append(dataset["info"].name)


RESULT_PATH = os.path.join(DATA_DIR, "result/")
if "result" not in os.listdir(DATA_DIR):
    os.mkdir(RESULT_PATH)

# create videos and datasets, upload videos
for ds_name in correct_datasets:
    FRAMES_PATH = os.path.join(DATA_DIR, ds_name)
    frames = [cv2.imread(path) for path in result_paths[ds_name]]
    out_size = frames[0].shape[0:2][::-1]
    cur_path = os.path.join(RESULT_PATH, ds_name)

    if ds_name not in os.listdir(RESULT_PATH):
        os.mkdir(cur_path)

    f.create_video_from_images(frames, cur_path + f"/{ds_name}.mp4", out_size)

    f.create_dataset_and_upload_result(g.api, g.project.id, f"{cur_path}/")

    # clean dir after each dataset perfoming
    if ds_name not in os.listdir(DATA_DIR):
        rmtree(FRAMES_PATH)


rmtree(DATA_DIR)
print("finish")
