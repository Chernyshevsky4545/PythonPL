#3. Порахувати кількість чисел, що більше за середнє.

import random

b=[]
for i in range(random.randint(1, 50)):
    b.append(random.randint(1, 100))


c=[]
ser=sum(b)/len(b)
print("Список:",b)
for a in b:
    if a>ser:
        c.append(a)
print("кількість чисел, що більше за середнє", len(c))