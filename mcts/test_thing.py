class Test:
    def __init__(self):
        self._a = 1

    @property
    def a(self):
        return self._a + 100

    @a.setter
    def a(self, value):
        self._a = value


t = Test()
print(t.a)
t.a += 1
print(t.a)
