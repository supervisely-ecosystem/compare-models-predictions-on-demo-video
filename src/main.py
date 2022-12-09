from collections import defaultdict
import os
from shutil import rmtree

import cv2
import imgaug.augmenters as iaa
import supervisely as sly

import functions as f
import globals as g

# TODO: save project name on grid on top of image (bottom center)

project_ids = list(map(int, os.environ["CONTEXT_PROJECTID"].split(",")))
DATA_DIR = sly.app.get_data_dir()
src_projects_data = defaultdict(dict)


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
first_project = next(iter(src_projects_data.values()))
all_projects = src_projects_data.values()
first_project = all_projects[0]


# check datasets, images and merge images to frames
for ds_num, (ds_name, dataset) in enumerate(first_project["datasets"].items()):
    FRAMES = 0

    ds_path = os.path.join(DATA_DIR, ds_name)
    if ds_name not in os.listdir(DATA_DIR):
        os.mkdir(ds_path)

    # nested list of all dataset`s names for all projects
    all_ds_names = [p["datasets"].keys() for p in all_projects]

    if not all(ds_name in p for p in all_ds_names):
        # skip this dataset if it`s name not in all projects
        continue

    for img_name, image_info in dataset["images"].items():

        # nested list of all image name for all datasets with same name
        all_img_names = [p["datasets"][ds_name]["images"].keys() for p in all_projects]

        if not all(img_name in d for d in all_img_names):
            # skip this image if it`s name not in all datasets with same name
            continue

        # temp lists for current frame
        temp_imgs = []
        temp_ann = []
        project_meta = []

        for pid, project in src_projects_data.items():

            img_id = project["datasets"][ds_name]["images"][image_info.name].id

            ann_json = g.api.annotation.download(img_id)
            project_meta = project["meta"]
            ann = sly.Annotation.from_json(ann_json.annotation, project_meta)

            img = g.api.image.download_np(img_id)
            ann.draw_pretty(img, thickness=3)
            temp_imgs.append(img)

        grid_size = f.get_grid_size(len(temp_imgs))
        frame = f.create_image_grid(temp_imgs, grid_size=grid_size)

        # create new videowriter if its the first frame in dataset
        if FRAMES == 0:
            height, width = frame.shape[:2]
            out_size = (width, height)
            videopath = ds_path + f"/{ds_name}.mp4"

            video_writer = cv2.VideoWriter(
                videopath, cv2.VideoWriter_fourcc(*"MP4V"), 0.5, out_size
            )

        # resize current frame if it differs from first video frame
        if frame.shape[0] > height:
            resize_aug = iaa.Resize({"height": height, "width": "keep-aspect-ratio"})
            frame = resize_aug(image=frame.copy())

        if frame.shape[1] > width:
            resize_aug = iaa.Resize({"height": height, "width": "keep-aspect-ratio"})
            frame = resize_aug(image=frame.copy())

        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        video_writer.write(frame_bgr)
        FRAMES += 1

    video_writer.release()
    f.create_dataset_and_upload_result(g.api, g.project.id, ds_path)
    rmtree(ds_path)

rmtree(DATA_DIR)
print("finish")
