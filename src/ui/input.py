from collections import defaultdict

import cv2
import os
import pandas as pd
import random
import supervisely as sly
from supervisely.app.widgets import Button, Card, Container, Field, Flexbox, Image
from supervisely.app.widgets import InputNumber, Progress, SelectProject, Table, PredictionsGallery
from supervisely.project.project_type import ProjectType


import src.globals as g
import src.ui.output as output

test_project_id=24504
test_dataset_id=71104
test_project_meta = sly.ProjectMeta.from_json(data=g.api.project.get_meta(id=test_project_id))

images_infos = g.api.image.get_list(dataset_id=test_dataset_id)
images_infos = sorted(images_infos, key=lambda image_info: image_info.name)
image_urls = [image_info.full_storage_url for image_info in images_infos]
image_ids = [image_info.id for image_info in images_infos]

titles = [image_info.name for image_info in images_infos]

anns_json = g.api.annotation.download_json_batch(dataset_id=test_dataset_id, image_ids=image_ids)
anns = [sly.Annotation.from_json(ann_json, test_project_meta) for ann_json in anns_json]

ground_truth_ann = anns[0]
ground_truth_url = image_urls[0]
anns_generator = (ann for ann in anns)

predictions_gallery = PredictionsGallery()

predictions_gallery.set_ground_truth(
    image_url=ground_truth_url,
    annotation=ground_truth_ann,
    title="Ground truth",
)
set_three = Button(text="add 3 predictions")
set_one = Button(text="add 1 prediction")
btn_container = Flexbox([set_three, set_one])

test_card = Card(
    title="Predictions Gallery",
    content=Container([predictions_gallery, btn_container]),
)
prediction_num = 0

@set_three.click
def set_btn_click_handler():
    global prediction_num
    predictions = []
    titles = []

    def _get_next_prediction(predictions, prediction_num):
        try:
            next_ann = next(anns_generator)
            predictions.append(next_ann)
            prediction_num += 1
            titles.append(f"Predictions {prediction_num} [treshold=0.5]")
            return prediction_num
        except StopIteration:
            pass

    prediction_num = _get_next_prediction(predictions, prediction_num)
    prediction_num = _get_next_prediction(predictions, prediction_num)
    prediction_num = _get_next_prediction(predictions, prediction_num)

    if len(predictions) > 0:
        predictions_gallery.add_predictions(annotations=predictions, titles=titles)


@set_one.click
def set_btn_click_handler():
    global prediction_num
    try:
        next_ann = next(anns_generator)
        prediction_num += 1
        predictions_gallery.add_prediction(next_ann, f"Predictions {prediction_num} [treshold=0.5]")
    except StopIteration:
        pass

# 1 input info
select_project = SelectProject(
    workspace_id=g.WORKSPACE_ID, compact=True, allowed_types=[ProjectType.IMAGES]
)
add_project_button = Button(text="Add project", icon="zmdi zmdi-plus")
input_progress = Progress()

start_card = Card(
    title="Select projects",
    description="1️⃣ Add projects to the table",
    content=Container([test_card, select_project, add_project_button, input_progress]),
)

# 2,3  explore info and preview example frame of future videos
table = Table(fixed_cols=1, width="100%")
table_card = Card(
    title="Selected projects",
    description="2️⃣ Information about selected projects",
    content=Container([table]),
    lock_message="Add projects to unlock",
)
table_card.lock()

preview_image = Image()
refresh_button = Button(text="Random frame preview", icon="zmdi zmdi-refresh")
preview_loading = False

input_opacity = InputNumber(value=40, min=0, max=100)
input_border = InputNumber(value=4, min=0, max=20)

opacity_field = Field(content=input_opacity, title="Opacity")
border_field = Field(content=input_border, title="Border width")

preview_settings = Flexbox([opacity_field, border_field])

preview_card = Card(
    title="Image preview",
    description="3️⃣ Preview video frame",
    content=Container([preview_settings, refresh_button, preview_image]),
    lock_message="Add projects to unlock",
)
preview_card.lock()

info = Container(
    widgets=[table_card, preview_card],
    direction="horizontal",
    gap=15,
    fractions=[1, 1],
)


@add_project_button.click
def collect_data():
    if output.render_loading or preview_loading:
        sly.app.show_dialog(
            title="Loading...",
            description="Please wait until the end before adding new projects.",
            status="error",
        )
        return
    table.loading = True
    refresh_button.disable()
    output.button_render.disable()

    collect_project_data(select_project.get_selected_id())
    table.read_pandas(get_table_data())

    output.info_success.hide()
    output.output_video.hide()

    table.loading = False
    table_card.unlock()
    preview_card.unlock()
    output.result_card.unlock()
    refresh_button.enable()
    output.button_render.enable()


@table.click
def remove_project(datapoint: Table.ClickedDataPoint):
    if datapoint.button_name is None:
        return
    if preview_loading or output.render_loading:
        sly.app.show_dialog(
            title="Loading...",
            description="Please wait until the end before removing the project.",
            status="error",
        )
        return
    table.loading = True
    refresh_button.disable()
    output.button_render.disable()
    add_project_button.disable()

    output.info_success.hide()
    output.output_video.hide()

    project_id = datapoint.row["id"]
    del g.src_projects_data[project_id]
    table.read_pandas(get_table_data())

    table_data = table.get_json_data()["table_data"]["data"]
    if len(table_data) == 0:
        table_card.lock()
        preview_card.lock()
        output.result_card.lock()
    else:
        refresh_button.enable()
        output.button_render.enable()
    table.loading = False
    add_project_button.enable()


@refresh_button.click
def refresh_preview():
    if table.loading:
        sly.app.show_dialog(
            title="Loading...",
            description="Please wait until the end before starting preview.",
            status="error",
        )
        return
    global preview_loading
    preview_loading = True
    add_project_button.disable()
    output.button_render.disable()

    opacity = input_opacity.get_value()
    border = input_border.get_value()
    details = (opacity, border)
    file_info = preview_frame(details)
    preview_image.set(url=file_info.full_storage_url)

    if not output.render_loading:
        add_project_button.enable()
        output.button_render.enable()
    preview_loading = False


def collect_project_data(id):
    id = 254750
    project_info = g.api.project.get_info_by_id(id)
    with input_progress(message="collecting data...", total=project_info.images_count) as pbar:
        meta_json = g.api.project.get_meta(id)
        g.src_projects_data[id]["meta"] = sly.ProjectMeta.from_json(meta_json)
        g.src_projects_data[id]["info"] = project_info

        # get project`s all datasets
        project_datasets = g.api.dataset.get_list(id)
        g.src_projects_data[id]["datasets"] = defaultdict()

        for ds in project_datasets:
            # get dataset`s all imageInfos
            ds_images = g.api.image.get_list(ds.id)
            images = defaultdict(dict)
            for image in ds_images:
                images[image.name] = image
                pbar.update(1)
            ds_data = {"info": ds, "images": images}
            g.src_projects_data[id]["datasets"][ds.name] = ds_data
            g.max_frames = max(g.max_frames, ds.images_count)
    output.input_frames.max = g.max_frames


def get_table_data():
    table_columns = ["id", "name", "datasets", "images_count", "remove"]
    rows = [
        [
            project["info"].id,
            project["info"].name,
            project["info"].datasets_count,
            project["info"].images_count,
            sly.app.widgets.Table.create_button("remove"),
        ]
        for project in g.src_projects_data.values()
    ]
    df = pd.DataFrame(rows, columns=table_columns)

    return df


def save_preview_image(api: sly.Api, frame, img_name):
    DATA_DIR = sly.app.get_data_dir()
    local_path = os.path.join(DATA_DIR, img_name)
    remote_path = os.path.join("", img_name)
    sly.image.write(local_path, frame)
    if api.file.exists(g.TEAM_ID, remote_path):
        api.file.remove(g.TEAM_ID, remote_path)
    file_info = api.file.upload(g.TEAM_ID, local_path, remote_path)
    return file_info


def preview_frame(deatails):
    opacity, thickness = deatails
    all_projects = g.src_projects_data.values()
    projects_count = len(all_projects)
    f_project = next(iter(all_projects))  # choose first project
    f_dataset = random.choice(list(f_project["datasets"].values()))  # choose first dataset
    if f_dataset is None:
        f_project = next(iter(all_projects))  # choose next project
        f_dataset = next(iter(f_project["datasets"].values()))
    f_img_info = random.choice(list(f_dataset["images"].values()))  # choose first image
    if f_img_info is None:
        f_dataset = next(iter(f_project["datasets"].values()))  # choose next dataset
        f_img_info = next(iter(f_dataset["images"].values()))
    f_img_shape = (f_img_info.height, f_img_info.width, 3)  # choose image size for preview

    ds_name = f_dataset["info"].name
    img_name = f_img_info.name
    grid_size = output.get_grid_size(projects_count)
    img = (img_name, f_img_info)
    frame = output.create_frame(
        ds_name, img, f_img_shape, grid_size, all_projects, opacity, thickness
    )
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    file_info = save_preview_image(g.api, frame, img_name)
    return file_info
