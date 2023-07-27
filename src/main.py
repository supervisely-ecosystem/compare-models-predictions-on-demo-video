import os

import supervisely as sly
from supervisely.app.widgets import Container


def main():
    import src.ui.input as input
    import src.ui.output as output


    layout = Container(widgets=[input.start_card, input.info, output.result_card], gap=15)

    app = sly.Application(layout=layout)
    raise ValueError("test")

if __name__ == "__main__":
    sly.main_wrapper("main", main)