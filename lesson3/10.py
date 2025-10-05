#10. Порахувати кількість чисел, рівних мінімальному значенню.
import random

b = []
for i in range(random.randint(1, 50)):
    b.append(random.randint(0, 100))
print("Список:", b)

m = min(b)
mi = b.count(m)
print("Мінімальне число:", m)
print("Кількість чисел, рівних мінімальному:", mi)