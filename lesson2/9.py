#9. Вивести середнє арифметичне всіх елементів масиву.

import random

b = []
for i in range(15):
    b.append(random.randint(1, 100))
print("Початковий масив:", b)

seredne = sum(b)/len(b)

print("Середнє арифметичне:",seredne)
