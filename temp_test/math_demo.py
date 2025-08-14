import math
# print("accbcd".rfind("c"))

# start = time.time()
# time.sleep(2)
# end = time.time()
# print(end - start)


def test():

    rst_set = set()
    print(3.2 // 1)
    print(2.2 // 1)

    print(math.floor(3.6))
    print(math.floor(3.2))

    rst_set.add(math.floor(2.2))
    rst_set.add(math.floor(1.6))
    rst_set.add(math.floor(0.6))
    rst_set.add(math.floor(-0.6))
    print(rst_set)
    print(0 in rst_set and 1 in rst_set and 2 in rst_set)
    print({0, 1, 2}.issubset(rst_set))
    print(rst_set.issuperset(range(3)))


if __name__ == '__main__':

    lst = [ 3, 1, 4, 1, 7, 2, 9, 8]
    #
    # for index in range(len(lst) - 1, -1, -1):
    #     print(lst[index])
    # print(lst[10:])
    # print("   ".strip() == '')
    # print("  ".isspace())

    aa = "asdf.jpg"
    bb = "asdf.heelo.mp4"
    cc = "aabc123"

    print(aa.rfind("."))
    print(bb[bb.rfind(".") + 1:])
    print(cc[cc.rfind(".") + 1:])
    print(aa.rindex("."))
    print(bb.rindex("."))
    print(cc.rindex("."))