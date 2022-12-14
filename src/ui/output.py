import glob
import os
import random
from shutil import rmtree

import cv2
import numpy as np
import supervisely as sly
from supervisely.imaging.font import get_readable_font_size
from supervisely.app.widgets import (
    Button,
    Card,
    Container,
    Checkbox,
    Field,
    Flexbox,
    Input,
    InputNumber,
)
from supervisely.app.widgets import NotificationBox, Progress, Select, VideoThumbnail

import src.globals as g
import src.ui.input as input


# 4 start render result video
input_frames = InputNumber(value=6, min=1, max=6)
input_frames_percents = InputNumber(value=100, min=1, max=100)
input_frames_percents.hide()

limits_types = [
    Select.Item(value="frames", label="frames"),
    Select.Item(value="percents", label="percents"),
]
select_frame_type = Select(items=limits_types)

frame_flex = Flexbox([select_frame_type, input_frames, input_frames_percents])
frames_field = Field(
    content=frame_flex,
    title="Sample frame count",
    description="Enter a number or percentage if you want to get a sample",
)

input_fps = InputNumber(value=5, min=0.1, max=400)
fps_field = Field(content=input_fps, title="fps", description="Set the number of frames per second")

is_random = Checkbox(content="")
random_field = Field(
    content=is_random,
    title="Random order of frames",
    description="Enable checkbox if you want to get a random frames",
)

render_settings = Field(
    content=Container([frames_field, random_field, fps_field]),
    title="Render Settings",
    description="Configuring the resulting video",
)

input_project_name = Input(placeholder="Enter the project name")
name_field = Field(
    content=input_project_name,
    title="Project name",
    description="Enter the destination project name",
)

button_render = Button(text="Start render")
settings_container = Container([render_settings, name_field, button_render])


ds_progress = Progress()
render_progress = Progress()

info_success = NotificationBox(title="Results uploaded to new project", box_type="success")
info_success.hide()

output_video = VideoThumbnail()
output_video.hide()


result_card = Card(
    title="Render video",
    description="4️⃣👇 Create new project and start rendering the video",
    content=Container(
        [settings_container, render_progress, ds_progress, info_success, output_video]
    ),
    lock_message="Add projects to unlock",
)
result_card.lock()


@select_frame_type.value_changed
def show_frames_input(value):
    if value == "percents":
        input_frames_percents.show()
        input_frames.hide()
    else:
        input_frames.show()
        input_frames_percents.hide()


@button_render.click
def create_project_and_upload_videos():
    input.button_add_project.disable()
    input.table_card.lock()
    info_success.hide()
    output_video.hide()

    project_name = input_project_name.get_value()
    fps = input_fps.get_value()
    frames_count = get_frames_count()
    opacity = input.input_opacity.get_value()
    thickness = input.input_border.get_value()
    random = is_random.is_checked()

    input_project_name.disable()
    if project_name == "":
        sly.app.show_dialog(
            title="Enter project name please",
            description="Please enter name to create a new project",
            status="error",
        )
        input_project_name.enable()
    else:
        details = (fps, opacity, thickness)
        video_info, _ = start_render_and_upload_to_new_project(
            project_name, details, frames_count, random
        )
        input_project_name.set_value("")
        info_success.show()
        output_video.set_video_id(video_info.id)
        output_video.show()
        input_project_name.enable()
        input.table_card.unlock()
    input.button_add_project.enable()


def get_frames_count():
    frames_count = None
    if select_frame_type.get_value() == "percents":
        project = next(iter(g.src_projects_data.values()))
        dataset = next(iter(project["datasets"].values()))
        all_frames = len(dataset["images"])
        frames_count = input_frames_percents.get_value() * all_frames // 100
        print(all_frames)
        print(input_frames_percents.get_value())
    else:
        frames_count = input_frames.get_value()
    return frames_count


def dataset_is_valid(all_projects, ds_name):
    #  check that the name of current dataset exists in all projects
    all_ds_names = [p["datasets"].keys() for p in all_projects]
    if not all(ds_name in p for p in all_ds_names):
        # skip this dataset if it`s name not in all projects
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


def get_random_key(all_keys):
    key = random.choice(list(all_keys))
    return key


def get_random_image(all_images, choosed_keys):
    key = random.choice(list(all_images.keys()))
    if key not in choosed_keys:
        return key, all_images[key]
    return get_random_image(all_images, choosed_keys)


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


def create_frame(ds_name, img, f_img_shape, grid_size, all_projects, opacity, thickness):
    img_name, image_info = img
    temp_imgs = []

    for project in all_projects:
        if not img_name in project["datasets"][ds_name]["images"].keys():
            # black rectangle if image is not exists in current dataset
            img = np.zeros(f_img_shape, dtype=np.uint8)
        else:
            img_id = project["datasets"][ds_name]["images"][image_info.name].id

            ann_json = g.api.annotation.download(img_id)
            ann = sly.Annotation.from_json(ann_json.annotation, project["meta"])

            img = g.api.image.download_np(img_id).astype("uint8")
            ann.draw_pretty(img, thickness=thickness, opacity=(opacity / 100))
            if img.shape[:2] != f_img_shape[:2]:
                img = check_and_resize_image(img, f_img_shape[:2])

        project_name = project["info"].name
        img = draw_text(img, project_name)
        temp_imgs.append(img)

    rows, cols = grid_size
    frame = create_image_grid(temp_imgs, grid_size=(rows, cols))
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    return frame


def save_preview_image(api: sly.Api, frame, img_name):
    DATA_DIR = sly.app.get_data_dir()
    local_path = os.path.join(DATA_DIR, img_name)
    remote_path = os.path.join("", img_name)
    sly.image.write(local_path, frame)
    if api.file.exists(g.TEAM_ID.id, remote_path):
        api.file.remove(g.TEAM_ID.id, remote_path)
    file_info = api.file.upload(g.TEAM_ID.id, local_path, remote_path)
    return file_info


def preview_frame(deatails):
    opacity, thickness = deatails
    all_projects = g.src_projects_data.values()
    projects_count = len(all_projects)
    f_project = next(iter(all_projects))  # choose first project
    f_dataset = next(iter(f_project["datasets"].values()))  # choose first dataset
    if f_dataset is None:
        f_project = next(iter(all_projects))  # choose next project
        f_dataset = next(iter(f_project["datasets"].values()))
    f_img_info = next(iter(f_dataset["images"].values()))  # choose first image
    if f_img_info is None:
        f_dataset = next(iter(f_project["datasets"].values()))  # choose next dataset
        f_img_info = next(iter(f_dataset["images"].values()))
    f_img_shape = (f_img_info.height, f_img_info.width, 3)  # choose image size for preview

    ds_name = f_dataset["info"].name
    img_name = f_img_info.name
    grid_size = get_grid_size(projects_count)
    img = (img_name, f_img_info)
    frame = create_frame(ds_name, img, f_img_shape, grid_size, all_projects, opacity, thickness)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    file_info = save_preview_image(g.api, frame, img_name)
    return file_info


def create_video_for_dataset(
    dataset, ds_name, ds_path, all_projects, details, frames_count, is_random
):
    fps, opacity, thickness = details

    # choose image size
    all_img_in_cur_ds = iter(dataset["images"].values())
    f_img_info = next(all_img_in_cur_ds)
    f_img_shape = (f_img_info.height, f_img_info.width, 3)

    # create new videowriter for current dataset
    videopath = ds_path + f"/{ds_name}.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"MP4V")
    height, width = f_img_shape[:2]
    grid = get_grid_size(len(all_projects))
    (rows, cols) = grid
    video_size = (width * cols, height * rows)
    video_writer = cv2.VideoWriter(videopath, fourcc, fps, video_size)
    frames_count = len(dataset["images"]) if frames_count is None else frames_count

    with ds_progress(message="processing images...", total=frames_count) as pbar:
        choosed_keys = []
        for img in dataset["images"].items():
            if frames_count == 0:
                break
            if is_random is not None:
                # img_name, img_info = get_random_image(dataset["images"], choosed_keys)
                # print(img_name)
                while True:
                    img_name = get_random_key(dataset["images"].keys())
                    img_info = dataset["images"][img_name]
                    if img_name not in choosed_keys:
                        break
                choosed_keys.append(img_name)

            frame = create_frame(
                ds_name, (img_name, img_info), f_img_shape, grid, all_projects, opacity, thickness
            )
            video_writer.write(frame)
            pbar.update(1)
            frames_count -= 1

    video_writer.release()


def create_project(project_name, api):
    # create new project and dataset
    project = api.project.create(
        g.WORKSPACE_ID, project_name, sly.ProjectType.VIDEOS, change_name_if_conflict=True
    )
    print(f"New project has been sucessfully created (id={project.id})")
    return project.id


def create_dataset(project_id, api):
    dataset = api.dataset.create(
        project_id, name="compare NN predictions", change_name_if_conflict=True
    )
    print(f"New dataset has been sucessfully created (id={dataset.id})")
    return dataset.id


def upload_video(dataset_id, api, path):
    #  upload result video
    video_path = glob.glob(path + r"/*.mp4")[0]
    video_info = api.video.upload_path(dataset_id, name="Video", path=video_path)
    print(f"Result video (id={video_info[0]}) uploaded to the current dataset (id={dataset_id})")

    return video_info


def start_render_and_upload_to_new_project(project_name, datails, frames_count, random):
    # iterate over datasets, images, merge images to frames and write video fo each dataset
    DATA_DIR = sly.app.get_data_dir()  # temp directory to store result video before uploading
    all_projects = g.src_projects_data.values()
    f_project = next(iter(all_projects))  # take the first project for iterations

    project_id = create_project(project_name, g.api)

    with render_progress(message="processing datasets", total=len(f_project["datasets"])) as pbar:
        for ds_name, dataset in f_project["datasets"].items():
            projects_count = len(all_projects)  # to get frame size for datasets with current name

            if not dataset_is_valid(all_projects, ds_name):
                projects_count -= 1
                continue

            ds_path = os.path.join(DATA_DIR, ds_name)
            if ds_name not in os.listdir(DATA_DIR):
                os.mkdir(ds_path)

            create_video_for_dataset(
                dataset, ds_name, ds_path, all_projects, datails, frames_count, random
            )
            dataset_id = create_dataset(project_id, g.api)
            video_info = upload_video(dataset_id, g.api, ds_path)

            pbar.update(1)

            rmtree(ds_path)  # clean direcroty with uploaded video
    rmtree(DATA_DIR)  # clean temp directories
    return video_info, project_id
