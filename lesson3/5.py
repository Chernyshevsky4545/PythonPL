#5. Вивести індекси чисел, кратних 3.
import random

b=[]
for i in range(random.randint(1, 50)):
    b.append(random.randint(0, 100))
print(b)
index = 0
for x in b:
    if x % 3 == 0:
        print(index)
    index += 1
print(index)