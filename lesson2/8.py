#8. Переставити елементи масиву у зворотному порядку.

import random

b = []
for i in range(15):
    b.append(random.randint(1, 100))
print("Початковий масив:", b)

n=list(reversed(b))
print("Масив у зворотньому порядку",n)