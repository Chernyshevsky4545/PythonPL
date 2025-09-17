#7. Порахувати суму елементів масиву, які більші за задане число (k).

import random

b = []
for i in range(15):
    b.append(random.randint(1, 100))
print("Масив:", b)
k = int(input("Число: "))
suma = 0
for a in b:
    if a > k:
        suma += a

print("Сума елементів масиву, які більші за", k, ":", suma)