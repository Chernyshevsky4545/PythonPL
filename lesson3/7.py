#7. Знайти найбільший непарний елемент.
import random

b = []
for i in range(random.randint(1, 50)):
    b.append(random.randint(0, 100))
print("Список:", b)

c = []
for x in b:
    if x % 2 != 0:
        c.append(x)

if c:
    d = max(c)
    print("Найбільший непарний елемент:", d)
else:
    print("-")