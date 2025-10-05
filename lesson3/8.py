#8. Обчислити суму квадратів чисел на парних індексах.

import random

b = []
for i in range(random.randint(1, 50)):
    b.append(random.randint(0, 100))
print("Список:", b)

suma = 0
for i in range(0, len(b), 2):
    suma += b[i] ** 2

print(suma)
