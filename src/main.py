from collections import defaultdict
import os
from shutil import rmtree

import cv2
import numpy as np
import supervisely as sly

import functions as f
import globals as g

project_ids = list(map(int, os.environ["CONTEXT_PROJECTID"].split(",")))
DATA_DIR = sly.app.get_data_dir()  # temp directory to store result video before uploading


# collect all projects data
src_projects_data = defaultdict(dict)
for id in project_ids:
    project_info = g.api.project.get_info_by_id(id)
    meta_json = g.api.project.get_meta(id)
    src_projects_data[project_info.name]["meta"] = sly.ProjectMeta.from_json(meta_json)

    # get project`s all datasets
    project_datasets = g.api.dataset.get_list(id)
    for ds in project_datasets:

        # get dataset`s all imageInfos
        ds_images = g.api.image.get_list(ds.id)
        images = defaultdict(dict)
        for image in ds_images:
            images[image.name] = image

        src_projects_data[project_info.name]["datasets"] = defaultdict()
        ds_data = {"info": ds, "images": images}
        src_projects_data[project_info.name]["datasets"][ds.name] = ds_data


all_projects = src_projects_data.items()
f_project_name, f_project = next(iter(all_projects))  # take the first project for iterations


# iterate over datasets, images, merge images to frames and write video fo each dataset
for ds_name, dataset in f_project["datasets"].items():
    projects_count = len(all_projects)

    #  check that the name of current dataset exists in all projects
    all_ds_names = [p["datasets"].keys() for _, p in all_projects]
    if not all(ds_name in p for p in all_ds_names):
        # skip this dataset if it`s name not in all projects
        projects_count -= 1 # to fix the video frame size
        continue

    ds_path = os.path.join(DATA_DIR, ds_name)
    if ds_name not in os.listdir(DATA_DIR):
        os.mkdir(ds_path)

    # choose image size
    f_img_info = next(iter(dataset["images"].values()))
    f_img_shape = (f_img_info.height, f_img_info.width, 3)

    # create new videowriter for current dataset
    videopath = ds_path + f"/{ds_name}.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"MP4V")
    height, width = f_img_shape[:2]
    rows, cols = f.get_grid_size(projects_count)
    video_size = (width * cols, height * rows)
    video_writer = cv2.VideoWriter(videopath, fourcc, 0.5, video_size)

    for img_name, image_info in dataset["images"].items():
        temp_imgs, temp_ann = [], []

        for project_name, project in all_projects:
            if not img_name in project["datasets"][ds_name]["images"].keys():
                # black screen if image is not exists in current dataset
                img = np.zeros(f_img_shape, dtype=np.uint8)
            else:
                img_id = project["datasets"][ds_name]["images"][image_info.name].id

                ann_json = g.api.annotation.download(img_id)
                project_meta = project["meta"]
                ann = sly.Annotation.from_json(ann_json.annotation, project_meta)

                img = g.api.image.download_np(img_id).astype("uint8")
                ann.draw_pretty(img, thickness=3, opacity=0.2)
                if img.shape[:2] != f_img_shape[:2]:
                    img = f.check_and_resize_image(img, f_img_shape[:2])

            img = f.draw_text(img, project_name)
            temp_imgs.append(img)

        grid_size = f.get_grid_size(len(temp_imgs))
        frame = f.create_image_grid(temp_imgs, grid_size=grid_size)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        video_writer.write(frame)

    video_writer.release()
    f.create_dataset_and_upload_result(g.api, g.project.id, ds_path)

    rmtree(ds_path)  # clean direcroty with video

rmtree(DATA_DIR)
