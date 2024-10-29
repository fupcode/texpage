import hashlib
import hmac
import time
import urllib.parse


def get_auth(params):
    # 从参数中获取变量
    SecretId = params.get("SecretId")
    SecretKey = params.get("SecretKey")
    KeyTime = params.get("KeyTime")
    method = (params.get("method") or params.get("Method") or "put").lower()
    Query = params.get("Query", {})
    Headers = params.get("Headers", {})
    Pathname = params.get("Pathname", "")
    UseRawKey = params.get("UseRawKey", False)
    ForceSignHost = params.get("ForceSignHost", True)
    SystemClockOffset = params.get("SystemClockOffset", 0)
    Expires = params.get("Expires", 900)

    # 参数检查
    if not SecretId:
        raise ValueError("missing param SecretId")
    if not SecretKey:
        raise ValueError("missing param SecretKey")

    # 获取当前的时间戳，并计算签名有效期
    current_time = int(time.time() + SystemClockOffset)
    start_time = current_time - 1
    end_time = start_time + Expires
    key_time = KeyTime or f"{start_time};{end_time}"

    # 处理路径
    if not UseRawKey:
        Pathname = "/" + Pathname.lstrip("/")

    # 处理 Host 信息
    if ForceSignHost and "Host" not in Headers and "host" not in Headers:
        if params.get("Bucket") and params.get("Region"):
            Headers["Host"] = f"{params['Bucket']}.cos.{params['Region']}.myqcloud.com"

    # 构造签名信息
    header_keys = ";".join(sorted(k.lower() for k in Headers if k.lower().startswith("x-cos-") or k.lower() in ["host"]))
    query_keys = ";".join(sorted(Query.keys()))

    # 签名字符串
    sign_key = hmac.new(SecretKey.encode("utf-8"), key_time.encode("utf-8"), hashlib.sha1).hexdigest()
    http_string = ("\n".join([method, Pathname, urllib.parse.urlencode(Query), "", ""])).lower()
    string_to_sign = "\n".join(["sha1", key_time, hashlib.sha1(http_string.encode("utf-8")).hexdigest(), ""])
    signature = hmac.new(sign_key.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1).hexdigest()

    # 返回最终签名
    return "&".join([
        f"q-sign-algorithm=sha1",
        f"q-ak={SecretId}",
        f"q-sign-time={key_time}",
        f"q-key-time={key_time}",
        f"q-header-list={header_keys}",
        f"q-url-param-list={query_keys}",
        f"q-signature={signature}"
    ])


if __name__ == "__main__":
    # 示例调用
    params = {
        "SecretId": "AKIDg67OccirgjdEOE6peGovx3_gv8Q8o2Fvey8gCkDWi8YDekxjcINv55ZY-xAxLVR-",
        "SecretKey": "ULB46qJ11ZTchzEzFVwA7Ch+H75/pXIdsEfu2MRjs88=",
        "Pathname": "/math/057d45eb-7977-40c1-9856-c43af18b82c9",
        "Headers": {
            "Content-Length": 17328
        },
        "KeyTime": "1730144269;1730146069",
    }

    auth_signature = get_auth(params)
    print(auth_signature)
