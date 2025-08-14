from xypDebugConfig import printDeBugFlag
def xypPrint(*args, **kwargs):
    if printDeBugFlag:
        return print(*args, **kwargs)
if __name__ == "__main__":
    pass

