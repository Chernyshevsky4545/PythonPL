#2. Знайти суму парних чисел.

import random

b=[]
for i in range(random.randint(1, 50)):
    b.append(random.randint(1, 100))

c=0
for a in b:
    if a % 2 ==0:
        c+=a
print("Масив:",b)
print("Сума парних цифр", c)