import os

try:
    import dashscope
except Exception:
    print("dashscope 未安装")
    exit()

api_key = os.environ.get("DASHSCOPE_API_KEY")
if not api_key:
    print("no DASHSCOPE_API_KEY 未设置！")
    exit()

dashscope.api_key = api_key

prompt = "请用一句话介绍你自己。使用英文"

print("正在调用 Qwen API...")

resp = dashscope.Generation.call(
    model="qwen-turbo",
    prompt=prompt,
)

if resp.status_code == 200:
    print("yes 调用成功！")
    print("模型回答：", resp.output.text)
else:
    print("no 调用失败：")
    print("status:", resp.status_code)
    print(resp)

