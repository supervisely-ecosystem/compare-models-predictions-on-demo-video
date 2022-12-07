import glob
import os
import re
from shutil import rmtree

import cv2
import numpy as np
import supervisely as sly
from supervisely.io.fs import silent_remove

import stats as s
from excract_image import ExtractImageFromVideo


def perform_images_to_videos(src_datasets):
    # get nested list of all images of project
    src_images = [s.api.image.get_list(dataset[0].id) for dataset in src_datasets]

    for num, project_images in enumerate(src_images):
        vid_shape = None  # video shape for temp videos
        image_ids = []
        image_paths = []

        # create empty dir for temp images
        if str(num) in os.listdir(s.SOURCE_PATH):
            rmtree(s.SOURCE_PATH + str(num))
        os.mkdir(s.SOURCE_PATH + str(num))

        # control result video`s length
        if num == 0 or len(project_images) < s.min_frames:
            s.min_frames = len(project_images)

        # collect ids and paths of current dataset/project images
        for idx, image in enumerate(project_images):
            cur_shape = (image.width, image.height)
            if idx == 0:
                vid_shape = cur_shape

            image_paths.append(os.path.join(s.SOURCE_PATH, str(num), image.name))
            image_ids.append(image.id)

        # download images of current dataset/project
        s.api.image.download_paths(src_datasets[num][0].id, image_ids, image_paths)

        # create video
        video_path = os.path.join(s.SOURCE_PATH, f"merged-{num}.avi")
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        video = cv2.VideoWriter(video_path, fourcc, 1, vid_shape)

        for img_path in image_paths:

            img = cv2.imread(img_path)
            output = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            if output.shape[1::-1] != vid_shape:
                output = cv2.resize(output, vid_shape)
            if output is not None:
                video.write(output)
            else:
                video.write(img)
            silent_remove(img_path)

        rmtree(s.SOURCE_PATH + str(num))

        video.release()


def collect_videos_to_grid(src_path, res_path, min_frames):
    # search videos to merge
    videos_to_merge = glob.glob(src_path + r"*.avi")

    # collect titles for videos
    titles = [get_video_name(x) for x in videos_to_merge]

    # merge videos
    merge_videos(
        videos_to_merge,
        f"{res_path}merged.mp4",
        grid_size=get_grid_size(len(videos_to_merge)),  # get grid size
        titles=titles,
        title_position=(50, 70),
        max_frames=min_frames,
    )


def merge_videos(
    videos_in,
    video_out,
    grid_size=None,
    titles=None,
    title_position=(0.5, 0.5),
    max_frames: int = None,
):
    texts = titles
    if texts is None:
        texts = [None] * len(videos_in)
    assert len(videos_in) == len(texts)

    dir_name = os.path.dirname(video_out)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    vid_handles = []  # list of (frame, text) tupples
    for v, text in zip(videos_in, texts):
        assert os.path.exists(v), f"{v} not exists!"
        vid_handles.append((ExtractImageFromVideo(v), text))

    # control result video`s length
    if max_frames is not None:
        assert max_frames > 0
        least_frames = max_frames
    else:
        least_frames = sorted([e.total_frames for e, _t in vid_handles])[0]

    # check frames sizes and correct if they differ
    least_size = sorted([e.size for e, _t in vid_handles])[0]
    gens = [e.extract(text=t, text_pos=title_position) for e, t in vid_handles]
    gens2 = [e.extract(text=t, text_pos=title_position) for e, t in vid_handles]

    cur_frames = np.array([cv2.resize(next(g), least_size) for g in gens2])
    frames_grid = create_image_grid(cur_frames, grid_size=grid_size)

    # fps = vid_handles[0][0].fps
    out_size = frames_grid.shape[0:2][::-1]

    # out_size = out_size[::-1]
    video_writer = cv2.VideoWriter(video_out, cv2.VideoWriter_fourcc(*"MP4V"), 0.5, out_size)

    for n in range(least_frames - 1):
        cur_frames = np.array([cv2.resize(next(g), least_size) for g in gens])
        frames_grid = create_image_grid(cur_frames, grid_size=grid_size)
        video_writer.write(frames_grid)
    video_writer.release()
    print(f"Output video saved... {video_out}")


def create_image_grid(images, grid_size):
    num, img_w, img_h = images.shape[0], images.shape[-2], images.shape[-3]

    grid_h, grid_w = grid_size

    # create simple grid with needed size
    grid = np.zeros(
        [grid_h * img_h, grid_w * img_w] + list(images.shape[-1:]),
        dtype=images.dtype,
    )
    # paste current frames to grid
    for idx in range(num):
        x = (idx % grid_w) * img_w
        y = (idx // grid_w) * img_h
        grid[y : y + img_h, x : x + img_w, ...] = images[idx]
    return grid


def get_video_name(filepath: str) -> str:
    filename = filepath.split("/")[-1]
    pattern = r"(?P<name>.*)\.mp4"
    text_match = re.search(pattern, filename)
    if text_match:
        name = text_match.group("name")
        return name
    return "None"


def get_grid_size(num: int = 1) -> tuple:
    # get num of cols andd rows in result grid
    cols = max(int(np.ceil(np.sqrt(num))), 1)
    rows = max((num - 1) // cols + 1, 1)
    return (rows, cols)


def create_project(api, workspace_id, path):
    # create new project and dataset
    project = api.project.create(
        workspace_id, "compare predictions", sly.ProjectType.VIDEOS, change_name_if_conflict=True
    )
    dataset = api.dataset.create(
        project.id, name="compare NN predictions", change_name_if_conflict=True
    )
    print(f"Project has been sucessfully created, id={project.id}")

    #  upload result video
    video_path = glob.glob(path + r"*.mp4")[0]
    video_info = api.video.upload_path(dataset.id, name="Video", path=video_path)

    # clean temp files
    rmtree(s.SOURCE_PATH)
    rmtree(s.RESULT_PATH)

    # return video info
    return video_info
