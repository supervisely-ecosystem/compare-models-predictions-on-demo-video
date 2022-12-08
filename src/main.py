from collections import defaultdict
import os
from shutil import rmtree

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
    FRAMES = []

    if not all(ds_name in p["datasets"].keys() for p in src_projects_data.values()):
        continue
    for img_name, image_info in dataset["images"].items():
        if not all(
            img_name in p["datasets"][ds_name]["images"].keys() for p in src_projects_data.values()
        ):
            continue
        temp_ann = []  # clean after each frame merging
        temp_imgs = []

        project_meta = []
        for pid, project in src_projects_data.items():

            img_id = project["datasets"][ds_name]["images"][image_info.name].id

            temp_ann.append(g.api.annotation.download(img_id))
            img = g.api.image.download_np(img_id)
            temp_imgs.append(img)
            project_meta.append(project["meta"])

            if len(temp_imgs) == len(src_projects_data.values()):
                images_ann = [
                    sly.Annotation.from_json(temp_ann[i].annotation, project_meta[i])
                    for i in range(len(temp_ann))
                ]
                for i in range(len(temp_imgs)):
                    images_ann[i].draw_pretty(temp_imgs[i], thickness=3)

                grid_size = f.get_grid_size(len(temp_imgs))
                frame = f.create_image_grid(temp_imgs, grid_size=grid_size)
                FRAMES.append(frame)

    correct_datasets.append(dataset["info"].name)


RESULT_PATH = os.path.join(DATA_DIR, "result/")
if "result" not in os.listdir(DATA_DIR):
    os.mkdir(RESULT_PATH)

# create videos and datasets, upload videos
for ds_name in correct_datasets:

    out_size = FRAMES[0].shape[0:2][::-1]
    cur_path = os.path.join(RESULT_PATH, ds_name)

    if ds_name not in os.listdir(RESULT_PATH):
        os.mkdir(cur_path)

    f.create_video_from_images(FRAMES, cur_path + f"/{ds_name}.mp4", out_size)

    f.create_dataset_and_upload_result(g.api, g.project.id, f"{cur_path}/")


rmtree(DATA_DIR)
print("finish")
