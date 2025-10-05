#1. Створити список випадкових чисел.


import random

b=[]
for i in range(random.randint(1, 100)):
    b.append(random.randint(1, 100))
print(b)