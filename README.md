# TexPage 公式识别命令行工具

这是一个命令行工具，旨在通过命令行快捷使用texpage.com网站上的实用功能，功能其一为从图片里识别出latex公式；其二为AI润色文本。

使用该工具最好订阅 Texpage，如果你的学校订阅了 TexPage ，OCR识别公式和 AI 润色功能可以无限制使用；否则，免费版识别公式只能10次/月，AI 润色5次每天。

TexPage官网：https://www.texpage.com/

## 安装依赖

首先，克隆项目并安装依赖： 

```bash
git clone https://github.com/fupcode/texpage.git
cd texpage
pip install -r requirements.txt
```

## 初始化配置

该工具使用需要 Texpage 账号，即[登 录 - TeXPage](https://www.texpage.com/login)页面需要的账号和密码，注意不是高校的个人登录账号，需要主动注册。

学校已经订阅的可以参考南京大学的教程来注册带订阅的 Texpage 账号：[注册、登录与在校验证 | e-Science Document](https://doc.nju.edu.cn/books/latex/page/d09bf)。

在首次运行该工具时，需要初始化账号和密码配置。运行以下命令来初始化：

```bash
python tex.py init
```

根据提示输入你的账号和密码。成功后，账号和密码将保存在该目录下的 `config.json` 文件中，以便后续使用。再次使用命令可以修改账号密码。

## 使用示例

### 1. OCR 识别

OCR 识别功能可以从图片文件或剪切板中提取公式图像并进行识别。

#### 从本地图片文件进行识别：

```bash
python tex.py ocr -f /path/to/image.png
```

#### 从剪切板中获取图片进行识别：

将公式图片复制到剪切板，然后运行：

```python
python tex.py ocr -c
```

### 2. 文本润色

文本润色功能可以润色提供的文本，支持从剪切板中获取文本或直接输入需要润色的文本。

#### 从字符串进行润色：

```bash
python tex.py polish -s "This is a sample text that needs polishing."
```

#### 从剪切板中获取文本进行润色：

将文本复制到剪切板，然后运行：

```bash
python tex.py polish -c
```

