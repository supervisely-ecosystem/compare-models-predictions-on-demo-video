import cv2
import os


class ExtractImageFromVideo(object):
    def __init__(self, path):
        assert os.path.exists(path)

        self._p = path
        self._vc = cv2.VideoCapture(self._p)

        self.size = int(self._vc.get(cv2.CAP_PROP_FRAME_WIDTH)), int(
            self._vc.get(cv2.CAP_PROP_FRAME_HEIGHT)
        )
        self.fps = int(self._vc.get(cv2.CAP_PROP_FPS))
        self.total_frames = int(self._vc.get(cv2.CAP_PROP_FRAME_COUNT))

        self._start = 0
        self._count = self.total_frames

    def __del__(self):
        self.release()

    def extract(
        self,
        path=None,
        bgr2rgb=False,
        text=None,
        text_pos=None,
    ):
        if path is not None and not os.path.exists(path):
            os.makedirs(path)

        for i in range(0, self._count):
            success, frame = self._vc.read()
            if not success:
                print(f"index {i} exceeded.")
                break
            if path is not None:
                cv2.imwrite(
                    os.path.join(
                        path,
                        f"{self._start + i}.jpg",
                    ),
                    frame,
                )
            if bgr2rgb:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if text is not None:
                if text_pos is not None:
                    pos = (text_pos[0], self.size[1] - text_pos[1])
                else:
                    pos = int(self.size[0] * 0.06), int(self.size[1] * 0.95)
                frame = cv2.putText(
                    frame,
                    text,
                    pos,
                    cv2.FONT_HERSHEY_DUPLEX,
                    2,
                    (255, 255, 255),
                    thickness=3,
                )
            yield frame

    def release(self):
        if self._vc is not None:
            self._vc.release()
