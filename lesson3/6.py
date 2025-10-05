#6. Скласти список лише з чисел, менших за 50.
import random

b=[]
for i in range(random.randint(1, 50)):
    b.append(random.randint(0, 100))
print(b)

c = []
for x in b:
    if x < 50:
        c.append(x)

print(c)