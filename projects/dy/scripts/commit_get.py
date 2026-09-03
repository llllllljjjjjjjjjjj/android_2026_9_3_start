import requests
import struct, base64, time

import frida, subprocess, time

ADB = r"D:\reserve_agent\skills-portable-test\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
HOOK = r"D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook21.js"
BASE_HDR = "cookie\r\npassport_csrf_token=441f7e5260f91551c264fe7e4ac152d8\r\nuser-agent\r\ncom.ss.android.ugc.aweme/380001 (Linux; U; Android 10; zh_CN_#Hans; Pixel 4; Build/QQ3A.200605.001)\r\naccept-encoding\r\ngzip, deflate, br"

_script = None
def oracle_connect():
    global _script
    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"])
    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    _script = dev.attach(pid).create_script(open(HOOK, encoding="utf-8").read())
    _script.load()
    time.sleep(2)

def gen_x_gorgon(url):
    if _script is None:
        oracle_connect()
    out = _script.exports_sync.oracle(url, BASE_HDR)   # 空 headers 会返回 NULL
    parts = out.split("\r\n")
    return parts[parts.index("X-Gorgon") + 1]

# 实验
print(gen_x_gorgon("https://log0-misc-lf.amemv.com/service/2/app_log/performance/p2/?aid=1128&device_id=2310516478094584"))



# 请替换为实际抓包获取的完整 URL（包含路径和参数）
url = "https://api5-core-lf.amemv.com/aweme/v2/comment/list/stream/"  # 缺少具体路径，请自行补充
ts = int(time.time())



headers = {
    "Host": "api5-core-lf.amemv.com",
    "Cookie": "passport_csrf_token=441f7e5260f91551c264fe7e4ac152d8; passport_csrf_token_default=441f7e5260f91551c264fe7e4ac152d8; store-region=cn-jx; store-region-src=did; install_id=305014557150939; ttreq=1$acc983328eca331511c6dc5dd3f013547253a032; odin_tt=32aad904d8b4f9885148b901fa0bafb3b3920f9d1652c08f8989dd5b3890209ab978eb52877f098d8e0f7624785eed182384758048bca5ad300326bfdf5e9c0c353e513a1b94c97e4ab6030b33a38823",
    "x-tt-dt": "AAAZFKVYPHMMRUSRVEMEQGSEI7O3C7PCMBRGH44LKRZ6SGNUQ6NJNLWNWVKHRDWVPOOEIXDLV2TKNR55KLSDIJ7WWBOBVFRJS4IFNZKKQ5H367DD2A6PKM4CRDPETP3YYVSRZY4HB4VGZAW4MAJYQSY",
    "activity_now_client": "1787719071071",
    "x-ss-req-ticket": "1787719070622",
    "x-vc-bdturing-sdk-version": "4.1.1.cn",
    "sdk-version": "2",
    "passport-sdk-settings": "device_transfer_s_0,device_transfer_ab_1",
    "passport-sdk-version": "601581",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "x-ss-stub": "DDB335F63C957F4C0DAED58D14DCDA08",
    "x-bd-content-encoding": "zstd",
    "x-tt-store-region": "cn-jx",
    "x-tt-store-region-src": "did",
    "x-tt-request-tag": "s=-1;p=0",
    "x-ss-dp": "1128",
    "x-tt-trace-id": "01-3c5c355a0d8356709ecacf8515c40468-3c5c355a0d835670-00",
    "user-agent": "com.ss.android.ugc.aweme/380001 (Linux; U; Android 10; zh_CN_#Hans; Pixel 4; Build/QQ3A.200605.001; Cronet/TTNetVersion:6f1e308d 2025-12-08 QuicVersion:21ac1950 2025-11-18)",
    "x-argus": "nm2Oag==",
    "x-gorgon": "840400410401ba16c958178920ad643cf6cfcb706429e77a13d8",
    "x-helios": "kZ69CPVQ5x41NOsYgNwcehfVZGMYyYXuloIUf2iz0qfUp5hw",
    "x-khronos": "1787719070",
    "x-ladon": "YmNdmA==",
    "x-medusa": "m22OarMmwaDXGIMpodggRrwAQjxsDwABLTVwYFktgXkBWEbGigqkSp0eQnMbibrK7gRiPYFtHDFip59rwHaIdevnEcKvh8iBBQQX6J5llLCrnkjrFjQ8bXaLrwocxRFv03qaQM8V0szuMphQc7CyWWNLjK8pQa8xnWpixjsHqd9LuiFXEA3EwnqraYm2VPhusbfK2maH8BYeeVfIhVJ5SGM9TAFW0Sm5pvp7AbUv1/P1KKItIkwqLRBLwBWs559fQs7QpnqWlg6/em0GHsdYJ66x2BQHfMtCAmsWNOFGbSPx+/Z5yo6Qlk1wEBxVM6bvVaKOZ55a7KEpAifxZ1R7+j36azN62AEghpJpL2IBeiagMkbppJ+LvR9R1HZ2mo7M1POii3ak4T2X9O3P5BEEBXWTBa98XOTHHZosZBHzXjWfnIaaz8t1q51G3RVD7oeiI2daT53D/Io4oyRHaiDeUxrBA6fBFdcIEvCrRlZCYIAkMLgUpL1weYrWAIbDFqU3wnu4wToklrQkTcuW9suG/JfaQszQ7uR9XBffd8Henbi6OsJpQ+FV3tZUBUn9bxgfJr7AYKCQqG95SaZtt2q3dohxHZMdRu2YmJB780tER7PmjJ8GiGlnh6DqEZcSMkepANkPIdFa0T1AMXBbd50pWuhOkvGli3zh2GNv7LE6uC/cjI8Gyv8HEXTfpf4PMdKZ//OnwuxyKr50jcIQ1CzOXZqOsxHFdiUzBE4RvrHCHW+ylDwRE9OPtNf8sI378BXyf0n1Yp09PdAzciXBsU29o9QvEHsbwkVlcW/Fvzwh6rCCOQTvdySMZuBCmPY2n13gCg7nHGd5f00/qm9NpWijsTeO9tdrPSH+dk+ZkZk1zU1KCbesB0cJ1aYBq17h2pXvAv7WOI/PoVJ1emnxbrMd+wVkQFJS/m43GSpCaDJoegUZ6l8ua+wPIkKds3YObnz937UYQ6bdO9xp65O1Z3MdUxE2whjYtdbLvGRrye039vBquDrubdb14nx7gekQrnbg9SqY+9W7hv/01EHqu4Hk0oml7srgsr9ewndCh0bLS4GEO54sf/kTbIMH6X4RSZii1Th5q9vKdl5ZhuWMHKNjsB0didnoNE1yi2LqbejVO9i0EqVLkBA7lCswC8fNFG26Ixj5KpoRq4tS1ZYzb72xXLAHOFzH8Vc/Kv0gA41WiHOO/UVUu+cIj1QF//nPBf/4y8Y6"
}
headers["x-khronos"] = str(ts)
headers["x-argus"] = base64.b64encode(struct.pack('<I', ts)).decode()
print("请求时间戳:", headers["x-argus"])

# 原始 --data-binary 的二进制内容，必须原样复制（此处为示例，可能因编码损坏）
# 建议从抓包工具中复制十六进制数据，然后使用 bytes.fromhex() 还原
# 以下为占位符，请替换为实际二进制数据（可从原始命令中直接粘贴，注意转义）
# data = b"(\xef\xbc\x8f...{e\x03"  # 请替换为完整二进制，或者从原始 curl 的 --data-binary 后直接复制

# try:
#     response = requests.post(url, headers=headers, data=data, timeout=10)
#     print("状态码:", response.status_code)
#     print("响应内容:", response.text[:200])  # 只打印前200字符
# except Exception as e:
#     print("请求异常:", e)