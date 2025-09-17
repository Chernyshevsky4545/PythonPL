#6. Створити масив із 15 випадкових чисел. Вивести лише непарні елементи масиву.

import random
b=[]
for i in range(15):
    b.append(random.randint(1,100))
c=[]

for a in b:
    if a % 2 != 0:
        c.append(a)

print("Масив:",b)
print("Непарні елементи:", c)

