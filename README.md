# GLaDOS 自动签到，实现无限白嫖

原仓库地址：https://github.com/lukesyy/glados_automation

复制了一个仓库，进行了些修改，防止原仓库被封

环境变量：`GLADOS_COOKIE`（必要） 和 `PUSHPLUS_TOKEN`（非必要）

`GLADOS_COOKIE`多个账号需使用 '&' 隔开，示例：cookie&cookie



# Github Actions

1. 点击右上角 **fork** 按钮
2. 在自己仓库中打开此项目
3. 将 `runGladosAction.yml` 放入 `.github/workflows` 文件夹下
4. 配置环境变量
5. 点亮右上角的星星 **star** 激活 actions
6. 然后点击 Actions 标签查看运行的详细状况

![image](https://user-images.githubusercontent.com/70319988/231369203-c812910a-963d-45b8-98a5-95b2623c25d7.png)
![image](https://user-images.githubusercontent.com/70319988/199923789-639e8295-b03e-4abd-858e-ff427015512a.png)
![image](https://user-images.githubusercontent.com/70319988/199923884-d81dd457-ecc5-4de9-b480-191d25217c47.png)

 # 青龙面板

直接把 glados_Qinglong.py 文件放到青龙里，环境变量同上

# Cookie 格式（2026-09 更新）

GLaDOS 已在 2026 年 9 月将登录 Cookie 名称从旧版 `koa:sess` 改为新版 `gld:sess`。

正确的 `GLADOS_COOKIE` 应类似：

```text
gld:sess=xxxxxx; gld:sess.sig=yyyyyy
```

如果浏览器里仍然只有 `koa:sess`，请先退出 GLaDOS 登录，再重新登录一次，让服务端下发新版 Cookie。
旧版 Cookie 会持续返回“没有权限”。
