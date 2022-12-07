import glob
from shutil import rmtree

import cv2
import numpy as np


def check_datasets(datasets):
    # check projects have same count and name of datasets
    for dss in datasets.values():
        check1 = all(len(i) == len(dss[0]) for i in dss)
        check2 = all(i.name == dss[0].name for i in dss)
        check3 = all(i.images_count == dss[0].images_count for i in dss)
        if not check1 == check2 == check3 == True:
            return False
    return True


def get_grid_size(num: int = 1) -> tuple:
    # get num of cols andd rows in result grid
    cols = max(int(np.ceil(np.sqrt(num))), 1)
    rows = max((num - 1) // cols + 1, 1)
    return (rows, cols)


def create_image_grid(images, grid_size):
    img_h, img_w = images[0].shape[:2]
    num = len(images)

    grid_h, grid_w = grid_size

    grid = np.zeros(
        [grid_h * img_h, grid_w * img_w] + list(images[0].shape[-1:]),
        dtype=images[0].dtype,
    )
    for idx in range(num):
        x = (idx % grid_w) * img_w
        y = (idx // grid_w) * img_h
        grid[y : y + img_h, x : x + img_w, ...] = images[idx]
    return grid


def create_video_from_images(images_mat, result_path, grid_size=1):
    zipped_images = zip(*images_mat)
    first_frame = create_image_grid(next(zipped_images), grid_size)
    out_size = first_frame.shape[0:2][::-1]
    video_writer = cv2.VideoWriter(result_path, cv2.VideoWriter_fourcc(*"MP4V"), 0.5, out_size)
    video_writer.write(first_frame)

    for i in range(len(images_mat[0]) - 1):
        frame = create_image_grid(next(zipped_images), grid_size)
        video_writer.write(frame)
    video_writer.release()


def create_dataset_and_upload_result(api, project_id, path):
    # create new project and dataset
    dataset = api.dataset.create(
        project_id, name="compare NN predictions", change_name_if_conflict=True
    )
    print(f"Dataset (id={dataset.id}) has been sucessfully created in project (id={project_id})")

    #  upload result video
    video_path = glob.glob(path + r"*.mp4")[0]
    video_info = api.video.upload_path(dataset.id, name="Video", path=video_path)
    rmtree(path)

    # return video info
    return video_info
