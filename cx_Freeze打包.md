# **cx_Freeze**

- **特点
官方推荐，目录结构干净

默认生成文件夹，**不会**出现 `_internal`；跨平台；配置简单。

- **使用步骤**

1. 安装

```bash
pip install cx-Freeze
```

2. 在项目根新建 `setup.py`

```python
from cx_Freeze import setup, Executable
setup(
 name="人物管理器",
 version="1.0",
 description="",
 executables=[Executable("app.py", base="Win32GUI")],
 options={
	 "build_exe": {
		 "include_files": ["people.json", "trash.json", "images"],
		 "build_exe": "dist/人物管理器"  # 输出目录
	 }
 }
)
```

3. 打包

```bash
python setup.py build
```

- **结果目录**

```
dist/PeoHub/
├── PeoHub.exe
├── people.json
├── trash.json
└── images/
```

无 `_internal`。
