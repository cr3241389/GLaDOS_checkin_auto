import json
import os
import re
import sys

import requests


REQUEST_TIMEOUT = 20
GLADOS_HOST = "glados.cloud"
CHECKIN_URL = "https://glados.cloud/api/user/checkin"
STATUS_URL = "https://glados.cloud/api/user/status"
PUSHPLUS_URL = "https://www.pushplus.plus/send"
COMMON_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "referer": "https://glados.cloud/console/checkin",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
}


def request_json(method, url, cookie, *, data=None):
    headers = {**COMMON_HEADERS, "cookie": cookie}
    if method.upper() != "GET":
        headers["origin"] = "https://glados.cloud"
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


def normalize_cookie(raw_cookie):
    cookie = raw_cookie.strip()
    if len(cookie) >= 2 and cookie[0] == cookie[-1] and cookie[0] in {'"', "'"}:
        cookie = cookie[1:-1].strip()

    if cookie.lower().startswith("cookie:"):
        cookie = cookie.split(":", 1)[1].strip()

    header_match = re.search(
        r"(?i)(?:-H|--header)\s+['\"]cookie:\s*([^'\"]+)",
        cookie,
    )
    if header_match:
        cookie = header_match.group(1).strip()

    cookie = re.sub(r"\s*\n\s*", "; ", cookie)
    cookie = re.sub(r";\s*", "; ", cookie)
    return cookie.strip()


def cookie_names(cookie):
    names = []
    for part in cookie.split(";"):
        if "=" not in part:
            continue
        name = part.split("=", 1)[0].strip()
        if name:
            names.append(name)
    return names


def validate_cookie_shape(cookie):
    names = cookie_names(cookie)
    lower_names = {name.lower() for name in names}
    print(
        f"::notice::GLADOS_COOKIE 格式检查：包含 {names or '无有效 Cookie 名称'}，"
        f"长度 {len(cookie)}"
    )

    if not names:
        print(
            "::error::GLADOS_COOKIE 格式不正确：没有检测到 Name=Value。"
            "请复制完整 Cookie 请求头，而不是只复制单独的 Value。"
        )
        return False

    has_old_sess = "koa:sess" in lower_names
    has_new_sess = "gld:sess" in lower_names
    has_new_sig = "gld:sess.sig" in lower_names

    if has_old_sess and not has_new_sess:
        print(
            "::error::检测到旧版 Cookie（koa:sess）。GLaDOS 已在 2026-09 改为 "
            "gld:sess；请退出登录后重新登录，再复制新的 Cookie。"
        )
        return False

    if has_new_sess and not has_new_sig:
        print(
            "::error::GLADOS_COOKIE 不完整：检测到 gld:sess，但缺少 gld:sess.sig。"
            "请把两个 Cookie 都复制进去。"
        )
        return False

    return True


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
        normalize_cookie(cookie)
        for cookie in os.environ.get("GLADOS_COOKIE", "").split("&")
        if cookie.strip()
    ]

    if not cookies:
        print("::error::未获取到 GLADOS_COOKIE secret，请在仓库 Secrets 中配置。")
        return 1

    send_content = []
    has_error = False

    for index, cookie in enumerate(cookies, start=1):
        if not validate_cookie_shape(cookie):
            has_error = True
            continue

        checkin = request_json(
            "POST",
            CHECKIN_URL,
            cookie,
            data=json.dumps({"token": GLADOS_HOST}),
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
