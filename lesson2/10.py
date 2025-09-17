#10. Знайти індекс максимального елемента у масиві.

import random

b = []
for i in range(15):
    b.append(random.randint(1, 100))
print("Масив:", b)

m = max(b)
n = b.index(m) +1

print("Індекс максимального елемента у масиві:", n)