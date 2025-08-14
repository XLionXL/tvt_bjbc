import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit


def fitFunc( x, a, b):  # 拟合函数
    return a / x + b


def lambdaFitFunc( x, y):
    args, _ = curve_fit(fitFunc, x, y)
    a, b = args
    if a <= 0:
        return (None, None, None)
    else:
        return (lambda v: a / v + b, a, b)


# headF, headA, headB = lambdaFitFunc([41.3 ,58.3 ], [ 339,302])
# footF, footA, footB = lambdaFitFunc([41.3 ,58.3 ], [ 322,290])
# a0,b0=5240.48411764705,212.11176470588254
# a1,b1=4532.310588235294,212.25882352941179

# headF, headA, headB = lambdaFitFunc([20.7,51 ], [438,296])
# footF, footA, footB = lambdaFitFunc([20.7,51], [406,281])

headF, headA, headB = lambdaFitFunc([73.5,147.1,190.3 ], [432,262, 221  ])
footF, footA, footB = lambdaFitFunc([73.5,147.1,190.3 ], [392,238,198   ])
print(headF, headA, headB)

print(footF, footA, footB )



# dd= a0/objY + b0 -  a1/objY + b1


x = np.arange(1, 1000)
plt.figure(1)
plt.plot(x, headA / x + headB, label="Head")
plt.plot(x, footA / x + footB, label="Foot")
# plt.plot(x, diffA / x + diffB)
# y = 1e-8
# x = diffA * (y - diffB)
# print(diffA, diffB)
# print((headF(x) + footF(x)) / 2)
plt.legend()
plt.show()