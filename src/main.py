import os

import supervisely as sly
from supervisely.app.widgets import Container

from src.ui.input import test_card
# import src.ui.output as output


# layout = Container(widgets=[input.start_card, input.info, output.result_card], gap=15)
layout = Container(widgets=[input.test_card])

app = sly.Application(layout=layout)