from collections import defaultdict

import pandas as pd
import supervisely as sly
from supervisely.app.widgets import Button, Card, Container, Input, LabeledImage
from supervisely.app.widgets import Progress, SelectProject, Table
from supervisely.project.project_type import ProjectType


import src.globals as g
import src.ui.output as output


# 1 input info
select = SelectProject(workspace_id=g.workspace.id, allowed_types=[ProjectType.IMAGES])
button_add_project = Button(text="Add project", icon="zmdi zmdi-plus")
input_progress = Progress()

start_card = Card(
    title="Collect data from projects",
    description="1️⃣👇 Press start to collect data from projects",
    content=Container([select, button_add_project, input_progress]),
)


# 2,3  explore info and preview example frame of future videos
table = Table(fixed_cols=1, width="100%")
table_card = Card(
    title="Selected projects",
    description="2️⃣👉 Information about selected projects",
    content=Container([table]),
    lock_message="Add projects to unlock",
)
table_card.lock()

frame = LabeledImage(
    annotations_opacity=0.5, show_opacity_slider=False, border_width=3, enable_zoom=False
)
refresh_button = Button(text="Refresh preview", icon="zmdi zmdi-refresh", button_size="small")
input_opacity = Input(placeholder="40 (opacity, %)", size="small", maxlength=3)
input_border = Input(placeholder="4 (border width)", size="small", maxlength=2)
preview_container = Container(
    [input_opacity, input_border, refresh_button],
    direction="horizontal",
    fractions=[18, 22, 60],
)

preview_card = Card(
    title="Image preview",
    description="3️⃣👇 Preview video`s frame",
    content=Container([preview_container, frame]),
    lock_message="Add projects to unlock",
)
preview_card.lock()

info = Container(
    widgets=[table_card, preview_card],
    direction="horizontal",
    gap=15,
    fractions=[1, 1],
)


@button_add_project.click
def collect_data():
    table.loading = True
    refresh_button.disable()
    output.button_render.disable()
    collect_project_data(select.get_selected_id())
    table.read_pandas(get_table_data())
    output.info_success.hide()
    output.output_video.hide()
    table_card.unlock()
    preview_card.unlock()
    output.result_card.unlock()
    refresh_button.enable()
    output.button_render.enable()
    table.loading = False


@table.click
def remove_project(datapoint: Table.ClickedDataPoint):
    if datapoint.button_name is None:
        return
    table.loading = True
    refresh_button.disable()
    project_id = datapoint.row["id"]
    del g.src_projects_data[project_id]
    table.read_pandas(get_table_data())
    output.info_success.hide()
    output.output_video.hide()
    table_data = table.get_json_data()["table_data"]["data"]
    if len(table_data) == 0:
        table_card.lock()
        preview_card.lock()
        output.result_card.lock()
    refresh_button.enable()
    table.loading = False


@refresh_button.click
def refresh_preview():
    table_card.lock()
    output.button_render.disable()
    opacity = check_field(input_opacity, 0, 100, 40)
    thickness = check_field(input_border, 0, 20, 4)

    details = (opacity, thickness)
    frame.loading = True
    file_info = output.preview_frame(details)
    frame.set(title="Preview of result video frame", image_url=file_info.full_storage_url)
    table_card.unlock()
    output.button_render.enable()
    frame.loading = False


def collect_project_data(id):
    project_info = g.api.project.get_info_by_id(id)
    with input_progress(message="collecting data...", total=project_info.images_count) as pbar:
        meta_json = g.api.project.get_meta(id)
        g.src_projects_data[id]["meta"] = sly.ProjectMeta.from_json(meta_json)
        g.src_projects_data[id]["info"] = project_info

        # get project`s all datasets
        project_datasets = g.api.dataset.get_list(id)
        for ds in project_datasets:
            # get dataset`s all imageInfos
            g.src_projects_data[id]["datasets"] = defaultdict()
            ds_images = g.api.image.get_list(ds.id)
            images = defaultdict(dict)
            for image in ds_images:
                images[image.name] = image
                pbar.update(1)
            ds_data = {"info": ds, "images": images}
            g.src_projects_data[id]["datasets"][ds.name] = ds_data


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


def check_field(field, min, max, default):
    if field.get_value() == "":
        field.set_value(default)
    num = field.get_value()
    if type(field.get_value()) == str:
        num = int(num)
    if num < min:
        field.set_value(min)
        num = min
    if num > max:
        field.set_value(max)
        num = max
    return num