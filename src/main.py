import stats as s
import functions as f


print("start")
f.perform_images_to_videos(s.src_datasets)
f.collect_videos_to_grid(s.SOURCE_PATH, s.RESULT_PATH, s.min_frames)
video_info = f.create_project(s.api, s.workspace.id, s.RESULT_PATH)
print(f"result video uploaded with id {video_info[0]}")
