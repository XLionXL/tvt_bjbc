import time


class HYSTERESIS_THRESHOLD:
    def __init__(self, threshold, hysteresis_coef=0.8):
        self.threshold = threshold
        self.hysteresis_coef = hysteresis_coef
        self.hysteresis_threshold = threshold

    def output(self, value):
        result = False
        if value >= self.hysteresis_threshold:
            result = True
            self.hysteresis_threshold = self.threshold * self.hysteresis_coef
        else:
            self.hysteresis_threshold = self.threshold
        return result


def test_hysteresis():
    hysteresis_threshold = HYSTERESIS_THRESHOLD(9)
    edge_detect=EDGE_DETECT(0)
    for index in range(10):
        value = index
        result = hysteresis_threshold.output(value)
        print(f"result={result},{value}/{hysteresis_threshold.hysteresis_threshold},{edge_detect.is_Edge(result)}")
    for index in range(10):
        value = 10 - index
        result = hysteresis_threshold.output(value)
        print(f"result={result},{value}/{hysteresis_threshold.hysteresis_threshold},{edge_detect.is_Edge(result)}")


class EDGE_DETECT():
    def __init__(self, init_value=-562536):
        # 562536 取奇怪值，使得第一次判定为is_edge为True
        self.lastValue = init_value
        self.last_edge_timestamp = time.time()
        self.last_rising_timestamp = time.time()
        self.last_falling_timestamp = time.time()

    def is_Edge(self, value):
        is_edge=True if value!=self.lastValue else False
        if is_edge:
            self.last_edge_timestamp = time.time()
        if value and not self.lastValue:
            self.last_rising_timestamp = time.time()
        if self.lastValue and not value:
            self.last_falling_timestamp = time.time()

        self.lastValue = value
        return is_edge



if __name__ == "__main__":
    test_hysteresis()

