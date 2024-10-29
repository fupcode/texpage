from datetime import datetime
from auth import get_auth
import requests
import json
import argparse
import os
import sys
import re
import uuid
import mimetypes
from PIL import ImageGrab, Image
import io


class TexClient:
    def __init__(self):
        os.environ['NO_PROXY'] = 'tex.nju.edu.cn; upload.texpage.com'
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(current_dir, 'config.json')

        self.account, self.password, self.session_id, self.expiry_time = self.load_config()

    def input_config(self):
        account = input("请输入账号: ")
        password = input("请输入密码: ")
        self.save_config(account, password)
        self.account, self.password, self.session_id, self.expiry_time = account, password, None, None

    def load_config(self):
        """从配置文件加载账号、密码、session_id 和 expiry_time，如果不存在则获取输入。"""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as file:
                config = json.load(file)
                account = config.get("account")
                password = config.get("password")
                session_id = config.get("session_id")
                expiry_time = config.get("expiry_time")

                # 转换 expiry_time 为 datetime 对象
                if expiry_time:
                    expiry_time = datetime.strptime(expiry_time, "%Y-%m-%dT%H:%M:%S")

                if account and password:
                    return account, password, session_id, expiry_time
        return None, None, None, None

    def save_config(self, account, password, session_id=None, expiry_time=None):
        """保存账号、密码、session_id 和 expiry_time 到配置文件中。"""
        config = {
            "account": account,
            "password": password,
            "session_id": session_id,
            "expiry_time": expiry_time.strftime("%Y-%m-%dT%H:%M:%S") if expiry_time else None
        }
        with open(self.config_path, "w") as file:
            json.dump(config, file)

    def login(self):
        """发送 POST 请求进行登录并获取 SESSIONID 和过期时间。"""
        url = "https://tex.nju.edu.cn/login"
        payload = {
            "account": self.account,
            "password": self.password
        }
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200 and 'set-cookie' in response.headers:
            # 获取 SESSIONID 和过期时间
            cookie_header = response.headers['set-cookie']
            self.session_id, self.expiry_time = self.extract_session_id_and_expiry(cookie_header)

            if self.session_id and self.expiry_time:
                # 更新配置文件
                self.save_config(self.account, self.password, self.session_id, self.expiry_time)
            else:
                raise Exception("登录失败，未能解析 SESSIONID 或过期时间")
        else:
            raise Exception("登录失败，请检查账号和密码")

    def extract_session_id_and_expiry(self, cookie_header):
        """解析 SESSIONID 和过期时间。"""

        # 使用正则表达式提取 SESSIONID 和 expires
        sessionid_pattern = r'SESSIONID=([^;]+)'  # 提取 SESSIONID 的值
        expires_pattern = r'expires=([^;]+)'  # 提取 expires 的值

        # 查找 SESSIONID
        sessionid_match = re.search(sessionid_pattern, cookie_header)
        sessionid = sessionid_match.group(1) if sessionid_match else None

        # 查找 expires
        expires_match = re.search(expires_pattern, cookie_header)
        expires = expires_match.group(1) if expires_match else None

        # 将过期时间转换为 UTC datetime
        expiry_time = datetime.strptime(expires, '%a, %d %b %Y %H:%M:%S GMT') if expires else None

        return sessionid, expiry_time

    def is_session_expired(self):
        """检查 SESSIONID 是否已过期。"""
        if self.expiry_time is None:
            # 如果没有过期时间，认为已过期，需要重新登录
            return True
        # 检查当前时间是否已经超过保存的过期时间
        return datetime.now() > self.expiry_time

    def inspect_config(self):
        if not self.account or not self.password:
            raise ValueError("账号和密码未设置, 请使用 init 命令初始化账号和密码")

    def get_cookie(self):
        """如果 SESSIONID 过期，重新登录，否则返回当前 SESSIONID。"""
        if self.is_session_expired():
            self.login()
        return {"SESSIONID": self.session_id}

    def ocr(self, mime_type, binary_data):
        """对图片进行 OCR 识别。"""
        def get_upload_token(cookie):
            url = "https://tex.nju.edu.cn/user/uploadToken?"
            params = {
                "t": int(datetime.now().timestamp() * 1000),
                "folder": "math"
            }
            response = requests.get(url, params=params, cookies=cookie)
            r = response.json()
            if response.status_code == 200 and r.get("status") and r["status"]["code"] == 1:
                return r["result"]
            else:
                return None

        def upload_image(mime_type, binary_data, file_uuid, token):
            path = "/math/" + file_uuid
            url = "https://upload.texpage.com" + path
            method = "put"
            auth = get_auth({
                "SecretId": token["credentials"]["tmpSecretId"],
                "SecretKey": token["credentials"]["tmpSecretKey"],
                "method": method,
                "Pathname": path,
                "Query": {},
            })
            header = {
                "Host": "upload.texpage.com",
                "Origin": "https://tex.nju.edu.cn",
                "Referer": "https://tex.nju.edu.cn/",

                "Authorization": auth,
                "Content-Type": mime_type,
                "x-cos-security-token": token["credentials"]["sessionToken"],
            }

            response = requests.put(url, data=binary_data, headers=header)
            if response.status_code != 200:
                raise Exception("上传图片失败\n请求头: \n" + str(response.request.headers) + "\n返回信息: \n" + response.text)

        def get_ocr_result(token, cookie):
            url = "https://tex.nju.edu.cn/api/user/math/upload"
            params = {
                "t": int(datetime.now().timestamp() * 1000),
            }
            payload = {
                "fileKey": "math/" + token
            }
            response = requests.post(url, json=payload, params=params, cookies=cookie)
            r = response.json()
            if response.status_code == 200 and r.get("status") and r["status"]["code"] == 1:
                return r["result"]
            else:
                raise Exception("获取 OCR 结果失败，返回信息: \n" + response.text)

        self.inspect_config()
        if self.is_session_expired():
            self.login()
        cookie = self.get_cookie()
        token = get_upload_token(cookie)
        if token is None:
            self.login()
            cookie = self.get_cookie()
            token = get_upload_token(cookie)
            if token is None:
                raise Exception("获取上传 token 失败")

        file_uuid = str(uuid.uuid4())

        upload_image(mime_type, binary_data, file_uuid, token)
        result = get_ocr_result(file_uuid, cookie)
        print(result)
        return result

    def polish(self, text):
        self.inspect_config()
        url = "https://tex.nju.edu.cn/api/ai/paraphrase"
        params = {
            "t": int(datetime.now().timestamp() * 1000),
        }
        payload = {
            "content": text
        }

        response = requests.post(url, json=payload, params=params)
        r = response.json()

        if response.status_code == 200 and r.get("status") and r["status"]["code"] == 1:
            print(r["result"])
            return r["result"]
        else:
            raise Exception("润色失败，返回信息: \n" + response.text)


def read_file_data(file_path):
    # 获取 MIME 类型
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "application/octet-stream"  # 默认为二进制流

    # 读取文件的二进制数据
    with open(file_path, "rb") as file:
        binary_data = file.read()

    return mime_type, binary_data


def get_clipboard_image():
    # 从剪切板读取图像
    image = ImageGrab.grabclipboard()

    if isinstance(image, Image.Image):
        # 检查图像格式
        if image.format == 'DIB':
            # 将 DIB 图像转换为 PNG 格式
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')  # 转换为 PNG 格式
            img_byte_arr.seek(0)  # 重置字节流的位置

            mime_type = "image/png"
            binary_data = img_byte_arr.getvalue()

            return mime_type, binary_data
        else:
            # 将其他图像保存到一个字节流中
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format=image.format)  # 使用原始图像格式
            img_byte_arr.seek(0)  # 重置字节流的位置

            # 获取 MIME 类型
            mime_type = f"image/{image.format.lower()}"
            binary_data = img_byte_arr.getvalue()

            return mime_type, binary_data
    else:
        raise ValueError("剪切板中没有有效的图像。")


def inspect_config(client):
    if not client.account or not client.password:
        raise ValueError("账号和密码未设置, 请使用 --init 选项初始化账号和密码")


def main():
    parser = argparse.ArgumentParser(description="TexPage 公式识别命令行工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # init 子命令
    subparsers.add_parser("init", help="初始化或重设账号和密码")

    # ocr 子命令
    ocr_parser = subparsers.add_parser("ocr", help="进行 OCR 识别")
    ocr_source_group = ocr_parser.add_mutually_exclusive_group(required=True)
    ocr_source_group.add_argument("-f", "--file", metavar="IMAGE_PATH", help="从 IMAGE_PATH 图片进行 OCR 识别")
    ocr_source_group.add_argument("-c", "--clip", action="store_true", help="获取剪切板中的图片进行 OCR 识别")

    # polish 子命令
    polish_parser = subparsers.add_parser("polish", help="润色提供的文本")
    polish_parser.add_argument("text", type=str, help="需要润色的文字")

    args = parser.parse_args()
    client = TexClient()

    # 根据不同的子命令执行相应的功能
    if args.command == "init":
        client.input_config()

    elif args.command == "ocr":
        if args.file:
            image_path = args.file
            if not os.path.exists(image_path):
                raise FileNotFoundError("文件不存在")
            mime_type, binary_data = read_file_data(image_path)
            client.ocr(mime_type, binary_data)
        elif args.clip:
            mime_type, binary_data = get_clipboard_image()
            client.ocr(mime_type, binary_data)

    elif args.command == "polish":
        text_to_polish = args.text
        client.polish(text_to_polish)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户终止程序", file=sys.stderr)
    except Exception as e:
        print(e, file=sys.stderr)
