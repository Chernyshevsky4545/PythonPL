#Вивести список у зворотному порядку.

import random

b = []
for i in range(random.randint(1, 50)):
    b.append(random.randint(0, 100))
print("Список:", b)

b.reverse()
print(b)