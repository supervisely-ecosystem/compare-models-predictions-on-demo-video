import glob

import cv2
import numpy as np
import supervisely as sly


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
        frame_bgr = cv2.cvtColor(frames[i], cv2.COLOR_RGB2BGR)
        video_writer.write(frame_bgr)
    video_writer.release()


def create_dataset_and_upload_result(api, project_id, path):
    # create new project and dataset
    dataset = api.dataset.create(
        project_id, name="compare NN predictions", change_name_if_conflict=True
    )
    print(f"Dataset (id={dataset.id}) has been sucessfully created in project (id={project_id})")

    #  upload result video
    video_path = glob.glob(path + r"/*.mp4")[0]
    video_info = api.video.upload_path(dataset.id, name="Video", path=video_path)

    # return video info
    return video_info


def get_readable_font_size(img_size):
    # return: size of font
    minimal_font_size = 6
    base_font_size = 14
    base_image_size = 512
    return max(
        minimal_font_size,
        round(base_font_size * (img_size[0] + img_size[1]) // 2) // base_image_size,
    )


def draw_text(img, pid):
    img_height, img_width = img.shape[:2]

    font_size = get_readable_font_size((img_width, img_height))
    font = sly.image.get_font(font_file_name=None, font_size=font_size)
    t_width, t_height = font.getsize(pid)
    x = int(img_width // 2 - t_width // 2)
    y = img_height - t_height * 1.5

    sly.image.draw_text(img, pid, (y, x), font=font)

    return img
