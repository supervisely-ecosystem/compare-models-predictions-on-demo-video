import glob

import cv2
import numpy as np
import supervisely as sly
from supervisely.imaging.font import get_readable_font_size


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


def check_and_resize_image(image, dim):
    # check if the width and height is specified
    if dim[:2] == image.shape[:2]:
        return image

    dim_h, dim_w = dim[:2]
    img_h, img_w = image.shape[:2]
    resized_img = np.zeros((dim_h, dim_w, 3), dtype=np.uint8)

    ratio_h = dim_h / img_h
    ratio_w = dim_w / img_w

    new_size = (0, 0)
    if img_h / dim_h > img_w / dim_w:
        new_size = (int(img_w * ratio_h), dim_h)
    else:
        new_size = (dim_w, int(img_h * ratio_w))
    new_img = cv2.resize(image, new_size)
    img_h, img_w = new_img.shape[:2]
    x = (dim_w - img_w) // 2
    y = (dim_h - img_h) // 2
    resized_img[y : y + img_h, x : x + img_w, ...] = new_img
    return resized_img


def draw_text(img, pid):
    img_h, img_w = img.shape[:2]
    font_size = get_readable_font_size((img_w, img_h))
    font = sly.image.get_font(font_file_name=None, font_size=font_size)
    t_width, t_height = font.getsize(pid)
    x = int(img_w // 2 - t_width // 2)
    y = img_h - t_height * 1.5

    sly.image.draw_text(img, pid, (y, x), font=font)

    return img


def create_dataset_and_upload_result(api, project_id, path):
    # create new project and dataset
    dataset = api.dataset.create(
        project_id, name="compare NN predictions", change_name_if_conflict=True
    )
    print(f"Dataset (id={dataset.id}) has been sucessfully created in project (id={project_id})")

    #  upload result video
    video_path = glob.glob(path + r"/*.mp4")[0]
    video_info = api.video.upload_path(dataset.id, name="Video", path=video_path)
    print(f"video (id={video_info[0]}) uploaded to the new dataset (id={dataset.id})")

    # return video info
    return video_info
