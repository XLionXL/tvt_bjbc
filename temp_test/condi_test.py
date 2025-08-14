# import datetime
# import threading
# import time
#
#
# class Account:
#     # 定义构造器
#     def __init__(self, account_no, balance):
#         # 封装账户编号、账户余额的两个成员变量
#         self.account_no = account_no
#         self._balance = balance
#         self.cond_balance = threading.Condition()
#         self.cond_deposit = threading.Condition()
#         self.cond_deposit_flag = 0
#
#     # 提供一个线程安全的draw()方法来完成取钱操作
#     def draw(self, draw_amount):
#         # 加锁,相当于调用Condition绑定的Lock的acquire()
#         self.cond_balance.acquire()
#         try:
#             # 如果self._flag为假，表明账户中还没有人存钱进去，取钱方法阻塞
#             if self._balance < draw_amount:
#                 self.cond_balance.wait()
#             # 执行取钱操作
#             self._balance -= draw_amount
#             print( f"{datetime.datetime.now().time()},{threading.current_thread().name} 取钱,余额为：{str(self._balance)}")
#             # 唤醒其他线程
#             self.cond_balance.notify_all()
#         # 使用finally块来释放锁
#         finally:
#             self.cond_balance.release()
#
#     def deposit(self, deposit_amount):
#         # 存钱锁
#         self.cond_deposit.acquire()
#         if self.cond_deposit_flag > 0:
#             self.cond_deposit.wait()
#         self.cond_deposit_flag += 1
#         # 加锁,相当于调用Condition绑定的Lock的acquire()
#         self.cond_balance.acquire()
#         try:
#             # 如果self._flag为真，表明账户中已有人存钱进去，存钱方法阻塞
#             if self._balance > 0:
#                 self.cond_balance.wait()
#             # 执行存款操作
#             self._balance += deposit_amount
#             print(f"{datetime.datetime.now().time()},{threading.current_thread().name} 存款, 余额为：{str(self._balance)}")
#             # 唤醒其他线程
#             self.cond_balance.notify_all()
#         # 使用finally块来释放锁
#         finally:
#             self.cond_balance.release()
#         # 释放存钱锁
#         self.cond_deposit_flag -= 1
#         self.cond_deposit.notify_all()
#         self.cond_deposit.release()
#         # 适当等待，避免总是被一个存钱者霸占存钱锁
#         time.sleep(0.001)
#
#
# #  定义一个函数，模拟重复max次执行取钱操作
# def draw_many(account, draw_amount, max):
#     for i in range(max):
#         account.draw(draw_amount)
#
#
# #  定义一个函数，模拟重复max次执行存款操作
# def deposit_many(account, deposit_amount, max):
#     for i in range(max):
#         account.deposit(deposit_amount)
#
#
# # 创建一个账户
# acct = Account("1234567", 0)
# # 创建、并启动一个“取钱”线程
# threading.Thread(name="取钱者", target=draw_many, args=(acct, 800, 300)).start()
# # 创建、并启动一个“存款”线程
# threading.Thread(name="存款者甲", target=deposit_many, args=(acct, 800, 100)).start()
# threading.Thread(name="存款者乙", target=deposit_many, args=(acct, 800, 100)).start()
# threading.Thread(name="存款者丙", target=deposit_many, args=(acct, 800, 100)).start()
