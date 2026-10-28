"""Image-cache scanning without multiprocessing named pipes on Windows."""
from concurrent.futures import ThreadPoolExecutor


class ImageThreadPool:
    def __init__(self, processes=None):
        self.executor = ThreadPoolExecutor(max_workers=processes)

    def imap(self, func, iterable):
        return self.executor.map(func, iterable)

    def __enter__(self):
        return self

    def __exit__(self, error_type, error, traceback):
        self.executor.shutdown(wait=True, cancel_futures=error_type is not None)


def configure_image_cache_threads():
    import ultralytics.data.base
    import ultralytics.data.dataset

    ultralytics.data.base.ThreadPool = ImageThreadPool
    ultralytics.data.dataset.ThreadPool = ImageThreadPool
