import os

import supervisely as sly
from supervisely.app.widgets import Container

import src.ui.input as input
import src.ui.output as output


layout = Container(widgets=[input.start_card, input.info, output.result_card], gap=15)

app = sly.Application(layout=layout)
