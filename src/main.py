from collections import defaultdict
import os
from shutil import rmtree

import cv2
import supervisely as sly

import functions as f
import stats as s


# get test data
###############################################################
project_ids = list(map(int, os.environ["CONTEXT_PROJECTID"].split(",")))

src_meta = []
src_datasets = defaultdict(list)
all_projects_datasets = []

for id in project_ids:
    meta_json = s.api.project.get_meta(id)
    meta = sly.ProjectMeta.from_json(meta_json)
    src_meta.append(meta)
    all_projects_datasets.append(s.api.dataset.get_list(id))

for ds_list in all_projects_datasets:
    for ds in ds_list:
        src_datasets[ds.name].append(ds)
#################################################################


try:
    f.check_datasets(src_datasets)
except Exception:
    raise ValueError("Error: current datasets have different structures")

for i, (ds_name, dss) in enumerate(src_datasets.items()):
    print(f"Loading images and annotations from {ds_name} datasets...")
    os.mkdir(s.TEMP_PATH + "results")
    RESULT_PATH = os.path.join(s.TEMP_PATH, "results/")
    result_path = f"{RESULT_PATH}merged.mp4"  # result video path
    ds_path = os.path.join(s.SOURCE_PATH, ds_name)  # current dataset temp directory
    grid_size = f.get_grid_size(len(dss))  # get result video grid size
    images_mat = []

    if ds_name not in os.listdir(s.SOURCE_PATH):
        os.mkdir(s.SOURCE_PATH + f"{ds_name}/")

    for ds_num, ds in enumerate(dss):
        # collecting image paths, ids
        ds_images = s.api.image.get_list(ds.id)
        images_ids = []
        images_path = []
        images_ann = []

        for num, img in enumerate(ds_images):
            images_ids.append(img.id)
            if str(num) not in os.listdir(ds_path):
                os.mkdir(ds_path + f"/{num}")
            img_path = os.path.join(ds_path, str(num), f"{ds_num}-{img.name}")
            images_path.append(img_path)

        # downloading all images and their annotations
        images_ann_json = s.api.annotation.download_batch(ds.id, images_ids)
        images_ann = [
            sly.Annotation.from_json(ann.annotation, src_meta[i]) for ann in images_ann_json
        ]
        s.api.image.download_paths(ds.id, images_ids, images_path)  # download dataset images

        # resize and annotate images before merging
        orig = [cv2.imread(path) for path in images_path]
        for j in range(len(orig)):
            images_ann[j].draw_pretty(orig[j], thickness=3)
        small = [cv2.resize(img, dsize=(0, 0), fx=0.5, fy=0.5) for img in orig]
        images_mat.append(small)

    f.create_video_from_images(images_mat, result_path=result_path, grid_size=grid_size)

    f.create_dataset_and_upload_result(s.api, s.project.id, RESULT_PATH)
    rmtree(ds_path)

# clean temp files
rmtree(s.TEMP_PATH)
print("finish")
