import glob
from shutil import rmtree

import cv2
import numpy as np


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


def create_video_from_images(frames, path, out_size):
    video_writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MP4V"), 0.5, out_size)

    for i in range(len(frames) - 1):
        video_writer.write(frames[i])
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
