import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

# 获取当前文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_dir, 'templates')

env = Environment(
    loader=FileSystemLoader(templates_dir),
    autoescape=False          # 渲染 Markdown 一般不需要 HTML 转义
)
# 告诉 Jinja2：遇到 .jinjia-md 也按模板解析
env.globals['__file_suffix__'] = '.jinjia-md'

def template(name: str, **kwargs) -> str:
    """
    根据模版名称获取模版
    :param name:  模版名称
    :return:
    """
    try:
        tmpl = env.get_template(f"{name}.jinjia-md")
        md_text = tmpl.render(**kwargs)
    except Exception as e:
        print(f"模板文件未找到: {templates_dir}/{name}.jinjia-md")
        print(f"当前搜索路径: {templates_dir}")
        print(f"目录是否存在: {os.path.exists(templates_dir)}")
        if os.path.exists(templates_dir):
            print(f"目录内容: {os.listdir(templates_dir)}")
        raise e

    return md_text

# 新增：把子模板内容注入到主模板
def render_with_sub(name_main: str, name_sub: str, **kwargs) -> str:
    """
    把子模板 name_sub 渲染结果作为变量 sub_content，
    再渲染主模板 name_main
    """
    sub_content = template(name_sub, **kwargs)  # 先渲
    result = template(name_main, systems_infos=sub_content, **kwargs)
    return result

def get_fin_prompt_template() -> str:
    """
    直接渲染返回财务系统提示信息
    """
    template_content = render_with_sub("main_prompt", "parameters")
    return template_content

if __name__ == "__main__":
    print(render_with_sub("fin-master", "systems-infos"))