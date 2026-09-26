import json
import os
import sys

import requests


REQUEST_TIMEOUT = 20
CHECKIN_URL = "https://glados.cloud/api/user/checkin"
STATUS_URL = "https://glados.cloud/api/user/status"
PUSHPLUS_URL = "https://www.pushplus.plus/send"
COMMON_HEADERS = {
    "referer": "https://glados.cloud/console/checkin",
    "origin": "https://glados.cloud",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/102.0.0.0 Safari/537.36"
    ),
}


def request_json(method, url, cookie, *, data=None):
    headers = {**COMMON_HEADERS, "cookie": cookie}
    if data is not None:
        headers["content-type"] = "application/json;charset=UTF-8"

    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            data=data,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        print(f"::error::请求 GLaDOS 失败: {exc}")
        return None

    try:
        payload = response.json()
    except ValueError:
        print(
            f"::error::GLaDOS 返回了非 JSON 内容 "
            f"(HTTP {response.status_code}): {response.text[:200]}"
        )
        return None

    if not response.ok:
        message = payload.get("message") if isinstance(payload, dict) else payload
        print(f"::error::GLaDOS HTTP {response.status_code}: {message}")
        return None

    return payload


def send_pushplus(token, title, content):
    if not token:
        return

    try:
        response = requests.get(
            PUSHPLUS_URL,
            params={"token": token, "title": title, "content": content},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"::warning::PushPlus 推送失败: {exc}")


def main():
    pushplus_token = os.environ.get("PUSHPLUS_TOKEN", "").strip()
    cookies = [
        cookie.strip()
        for cookie in os.environ.get("GLADOS_COOKIE", "").split("&")
        if cookie.strip()
    ]

    if not cookies:
        print("::error::未获取到 GLADOS_COOKIE secret，请在仓库 Secrets 中配置。")
        return 1

    send_content = []
    has_error = False

    for index, cookie in enumerate(cookies, start=1):
        checkin = request_json(
            "POST",
            CHECKIN_URL,
            cookie,
            data=json.dumps({"token": "glados.one"}),
        )
        state = request_json("GET", STATUS_URL, cookie)

        state_data = state.get("data") if isinstance(state, dict) else None
        if not isinstance(state_data, dict):
            message = state.get("message") if isinstance(state, dict) else "接口无有效返回"
            print(
                f"::error::账号 {index} 的 GLADOS_COOKIE 已失效或无权访问："
                f"{message}。请重新登录 GLaDOS 获取 Cookie，并更新仓库 Secret。"
            )
            has_error = True
            continue

        email = str(state_data.get("email") or f"账号{index}")
        left_days_raw = state_data.get("leftDays", "未知")
        left_days = str(left_days_raw).split(".")[0]

        if isinstance(checkin, dict):
            message = checkin.get("message") or checkin.get("msg") or "签到接口未返回消息"
            if checkin.get("code") == -2:
                has_error = True
        else:
            message = "签到接口无有效返回"
            has_error = True

        line = f"{email}----{message}----剩余({left_days})天"
        print(line)
        send_content.append(line)

    if send_content:
        send_pushplus(
            pushplus_token,
            "GLaDOS 签到成功",
            "\n".join(send_content),
        )

    if has_error:
        send_pushplus(
            pushplus_token,
            "GLaDOS 签到失败",
            "部分账号 Cookie 已失效或接口异常，请查看 GitHub Actions 日志。",
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
