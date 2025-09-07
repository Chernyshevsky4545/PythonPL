import math
a = int(input("Введіть число: "))
p = int(math.sqrt(a))   
if p*p == a:
    print("це квадрат числа:", p)
else:
    print("це не є квадратом цілого числа")
