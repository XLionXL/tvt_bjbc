from xypDebugConfig import opencvDeBugFlag
if opencvDeBugFlag:
    import cv2 as cv

def cvResize(*args, **kwargs):
    if opencvDeBugFlag:
        return cv.resize(*args, **kwargs)
def cvVideoCapture(*args, **kwargs):
    if opencvDeBugFlag:
        return cv.VideoCapture(*args, **kwargs)
def cvRectangle(*args, **kwargs):
    if opencvDeBugFlag:
        return cv.rectangle(*args, **kwargs)
def cvPutText(*args, **kwargs):
    if opencvDeBugFlag:
        return cv.putText(*args, **kwargs)

def cvWaitKey(*args, **kwargs):
    if opencvDeBugFlag:
        return cv.waitKey(*args, **kwargs)

def cvImshow(*args, **kwargs):
    if opencvDeBugFlag:
        return  cv.imshow(*args, **kwargs)

if __name__ == "__main__":
    pass
