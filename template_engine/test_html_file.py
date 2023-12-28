import numpy
import pandas

from template_engine.templite import Templite

with open("test.html") as f:
    content = f.readlines()


class Post:
    def __init__(self, title, timestamp, body):
        self.title = title
        self.timestamp = timestamp
        self.body = body


p1 = Post('1', '90', '3')
p2 = Post('2', '90', '3')
p3 = Post('3', '90', '3')
ctx = {'form': '测试', 'posts': [p1, p2, p3]}
text = "".join(content)
final_text = Templite(text).render(ctx)
# print(final_text)

with open('template_replace.html', 'w') as f:
    f.write(final_text)
