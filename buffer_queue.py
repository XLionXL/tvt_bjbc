from queue import Queue


class BufferQueue(Queue):
    """Slight modification of the standard Queue that discards the oldest item
    when adding an item and the queue is full.
    稍稍修改标准队列的逻辑：
    当队列满的时候添加数据，先移除掉最老的数据
    """

    def put(self, item, *args, **kwargs):
        # The base implementation, for reference:
        # https://github.com/python/cpython/blob/2.7/Lib/Queue.py#L107
        # https://github.com/python/cpython/blob/3.8/Lib/queue.py#L121
        with self.mutex:
            if 0 < self.maxsize == self._qsize():
                self._get()
            self._put(item)
            self.unfinished_tasks += 1
            self.not_empty.notify()
