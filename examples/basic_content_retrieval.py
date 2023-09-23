from metaphor_python import Metaphor

client = Metaphor("fa0fcc27-312c-4d5e-b06d-f101f9717e91")

ids = ["8U71IlQ5DUTdsZFherhhYA", "X3wd0PbJmAvhu_DQjDKA7A"]
response = client.get_contents(ids)

for content in response.contents:
    print(content.title, content.url)