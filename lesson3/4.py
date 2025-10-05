#4. Замінити всі нулі на `999`.
import random

b=[]
for i in range(random.randint(1, 50)):
    b.append(random.randint(0, 100))

c = []
for x in b:
    if x == 0:
        c.append(999)
    else:
        c.append(x)
b = c

print(b)