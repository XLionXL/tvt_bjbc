from blinker import signal

test_signal = signal('test_aa')


def subscrib(sender, **kw):
    print("Got a signal send by:", sender)
    return "aaaaaaaaa"


@test_signal.connect
def subscriber1(sender, **kwargs):
    print(f"subscriber1: {sender} kw:{kwargs}", )
    return 'received!'


@test_signal.connect_via("gg")
def subscriber2(sender, **kwargs):
    print(f"subscriber2: {sender} kw:{kwargs}", )
    return 'received!'


# @test_signal.connect_via("gaga")
# def subscriber2(sender, **kwargs):
#     print(sender, kwargs)
#
#
# @test_signal.connect_via("haha", test_signal)
# def subscriber3(sender, **kwargs):
#     print(sender, kwargs)


if __name__ == '__main__':
    # publish()

    result = test_signal.send('gg', abc=111)
    print(result)

    print("---------------------------------")

    result = test_signal.send('anonymous', abcd=1234)
    print(result)

    print("---------------------------------")
    test_signal.connect(subscrib)
    result = test_signal.send("haha")
    print(result)
