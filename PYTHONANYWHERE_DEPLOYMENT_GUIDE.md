# 在 PythonAnywhere 上部署 GOST 隧道管理器

本指南概述了将 GOST 隧道管理器 Flask 应用部署到 PythonAnywhere 的步骤。

## 1. 账户设置

*   **注册：** 如果您还没有账户，请在 [www.pythonanywhere.com](https://www.pythonanywhere.com) 注册。免费套餐（“Beginner”账户）应足以运行此应用程序，但请注意其限制。

## 2. 上传应用程序文件

您有几种选择：

*   **选项 A：Git 克隆 (如果您的代码在 Git 仓库中，推荐此方法)**
    1.  从您的 PythonAnywhere 控制面板打开一个 **Bash Console**。
    2.  克隆您的仓库：
        ```bash
        git clone <your_repository_url> YourProjectDirName
        cd YourProjectDirName
        ```
        将 `<your_repository_url>` 替换为您的 Git 仓库 URL，并将 `YourProjectDirName` 替换为您想要的项目目录名称（例如 `gost-tunnel-manager`）。

*   **选项 B：上传 ZIP 文件**
    1.  创建您的项目目录的 ZIP 文件（确保包含 `app.py`、`models.py`、`utils.py`、`gost_config_generator.py`、`requirements.txt`、`wsgi_template.py` 以及 `templates`、`static`、`translations` 文件夹）。
    2.  转到 PythonAnywhere 上的 **Files** 标签页。
    3.  导航到您想要上传项目的目录（例如，创建一个新目录，如 `gost-tunnel-manager`）。
    4.  使用 **Upload a file** 按钮。请注意，PythonAnywhere 的免费套餐对文件大小有限制。对于较大的项目，首选 `git`。
    5.  如果您上传了 ZIP 文件，您需要在 Bash Console 中解压它：
        ```bash
        unzip your_project_files.zip -d YourProjectDirName
        cd YourProjectDirName
        ```

## 3. 虚拟环境设置

使用虚拟环境至关重要。

1.  在您的 Bash Console 中，导航到您的项目目录：
    ```bash
    cd /home/YourUserName/YourProjectDirName 
    # 相应地替换 YourUserName 和 YourProjectDirName
    ```
2.  创建一个虚拟环境。选择您的代码支持的 Python 版本（例如 Python 3.10）：
    ```bash
    mkvirtualenv --python=/usr/bin/python3.10 myenv 
    # 'myenv' 可以是您虚拟环境的任何名称
    ```
    您的控制台提示符应发生变化，以表明您处于虚拟环境中（例如 `(myenv) $`）。
3.  安装依赖项：
    ```bash
    pip install -r requirements.txt
    ```

## 4. Web 应用配置

1.  转到您的 PythonAnywhere 控制面板上的 **Web** 标签页。
2.  点击 **Add a new web app**。
    *   确认您的域名（例如 `YourUserName.pythonanywhere.com`）。
    *   选择 **Manual configuration (including virtualenvs)**。
    *   选择您用于虚拟环境的 Python 版本（例如 Python 3.10）。
    *   PythonAnywhere 将创建您的 Web 应用并将您带到配置页面。

3.  **Virtualenv (虚拟环境):**
    *   滚动到 "Virtualenv" 部分。
    *   输入您的虚拟环境路径：`/home/YourUserName/.virtualenvs/myenv`（如果您使用了不同的名称，请替换 `YourUserName` 和 `myenv`）。

4.  **Code (Paths) (代码路径):**
    *   **Source code (源代码):** 将此设置为您的项目主目录：`/home/YourUserName/YourProjectDirName`
    *   **Working directory (工作目录):** 将此设置为相同的路径：`/home/YourUserName/YourProjectDirName`

5.  **WSGI Configuration File (WSGI 配置文件):**
    *   滚动到 "Code" 部分。点击 "WSGI configuration file" 链接（它可能类似于 `/var/www/YourUserName_pythonanywhere_com_wsgi.py`）。
    *   编辑此文件。删除默认内容，并用您的 `wsgi_template.py` 文件中的内容替换它，进行必要的修改。

    *   **您的 WSGI 文件的关键修改：**
        *   将 `project_home = u'/home/YourUserName/YourProjectDirName'` 更改为您的实际项目路径。
        *   确保 `from app import app as application` 正确指向您的 Flask 应用实例。
        *   如果 `os.makedirs(app.instance_path)` 存在且应用具有权限，则 `instance` 文件夹应由 `app.py` 自动创建。默认的 SQLite 数据库和 `gost_config.json` 将存储在此处。

        **示例 `wsgi.py` 内容 (改编自 `wsgi_template.py`):**
        ```python
        import sys
        import os

        # PythonAnywhere 上您的项目目录路径
        project_home = u'/home/YourUserName/YourProjectDirName' 
        if project_home not in sys.path:
            sys.path = [project_home] + sys.path

        # 设置环境变量 (FERNET_KEY 最好通过 Web 标签页 UI 设置)
        # os.environ['FLASK_APP'] = 'app.py' # 对于 WSGI 不是必需的，但对 flask 命令有好处
        # os.environ['FLASK_ENV'] = 'production' 

        from app import app as application

        # 可选：如果数据库未在其他地方处理且在生产环境中是安全的，则初始化数据库
        # with application.app_context():
        #    from app import init_db
        #    init_db() 
        ```

## 5. 静态文件配置 (Static Files Configuration)

1.  在 **Web** 标签页上，滚动到 "Static files" 部分。
2.  点击 **Add a new static file mapping**。
    *   **URL:** `/static`
    *   **Directory (目录):** `/home/YourUserName/YourProjectDirName/static` (替换为您的实际路径)

## 6. 环境变量 (Environment Variables)

1.  在 **Web** 标签页上，滚动到 "Environment variables" 部分。
2.  添加以下环境变量：
    *   `FERNET_ENCRYPTION_KEY`: 粘贴您生成的 **生产环境** Fernet 密钥。**这对安全至关重要。**
    *   `FLASK_APP` (可选，但推荐): `app.py`
    *   `FLASK_ENV` (可选): `production` (或用于调试的 `development`，但上线时应切换到 `production`)。
    *   `DATABASE_URL` (可选): 如果您决定使用 PythonAnywhere 提供的更强大的数据库（如 PostgreSQL 或 MySQL，付费功能），您需要在此处设置其连接字符串。否则，应用将默认使用 instance 文件夹中的 SQLite。

## 7. 数据库 (Database)

*   应用程序配置为使用 SQLite。当应用首次尝试访问数据库时，数据库文件 (`default.db`) 将自动在您的项目工作目录内的 `instance` 文件夹中创建（例如 `/home/YourUserName/YourProjectDirName/instance/default.db`）。
*   `instance` 文件夹的创建由 `app.py` 处理。

## 8. 重载 Web 应用 (Reloading the Web App)

*   对代码、WSGI 文件或环境变量进行任何更改后，转到 **Web** 标签页，然后点击 **Reload YourUserName.pythonanywhere.com** 按钮（绿色按钮）。
*   等待片刻让应用重载。

## 9. 访问日志 (Accessing Logs)

*   **Error Log (错误日志):** 位于 **Web** 标签页的 "Log files" 部分。此日志 (`error.log`) 显示 Python 错误和追溯信息。
*   **Server Log (服务器日志):** 同样在 "Log files" 中。此日志 (`server.log`) 显示对您的应用的请求、状态码等。
*   **Access Log (访问日志):** 显示 Web 服务器的访问详情。
*   如果您的应用程序未按预期工作，请首先检查这些日志。

## 10. PythonAnywhere 上的 GOST 限制 (关键)

GOST 隧道管理器应用程序旨在生成 GOST 配置文件，并可以尝试使用 `systemctl` 控制本地 GOST 服务。但是，在 PythonAnywhere 上（尤其是免费套餐），您**没有 `sudo` 访问权限**，并且无法通过 `systemctl` 运行像 `gost.service` 这样的系统级服务。

*   **`sudo systemctl` 命令将失败：** 应用程序中尝试运行 `sudo systemctl restart gost.service`（或 `start`、`stop`）的部分将会失败。该应用程序设计为捕获这些错误并显示消息。
*   **`gost_config.json` 路径：** 应用程序已修改为将其 `gost_config.json` 保存到其 `instance` 文件夹中（例如 `/home/YourUserName/YourProjectDirName/instance/gost_config.json`）。
*   **手动运行 GOST：**
    1.  您需要在您的 PythonAnywhere 账户中**手动安装 GOST**（例如，将二进制文件下载到您的主目录）。
    2.  您必须以**用户进程**的形式运行 GOST。您可以从 Bash console 执行此操作。
    3.  您需要配置您手动运行的 GOST 实例以使用此 Web 应用程序生成的 `gost_config.json` 文件。例如：
        ```bash
        # 在 PythonAnywhere Bash console 中
        /path/to/your/gost -C /home/YourUserName/YourProjectDirName/instance/gost_config.json
        ```
    4.  **进程管理：**
        *   要在关闭控制台后保持 GOST 运行，您可以使用 `nohup ... &` 或研究 PythonAnywhere 的 "Always-on tasks"（付费功能，但如果配置更改，可能可以编写脚本来检查/重启 GOST）。
        *   Web 应用中的 "应用配置并重启GOST" 按钮将在 instance 文件夹中生成 `gost_config.json` 文件。但是，"重启GOST" 部分将失败，并且 Web 应用将显示有关此内容的错误消息。如果您的 GOST 进程已在运行，您需要手动重启它以获取新配置。

**GOST 总结：** Web 应用程序可以管理 GOST 的*配置*，但您需要在 PythonAnywhere 上负责运行和管理 GOST *进程*本身。

## 11. 首次运行和数据库初始化
*   部署并重载 Web 应用后，当您首次访问使用数据库的页面时，`init_db()` 函数（通过 `app.py` 或您的 WSGI 设置调用）应在 `instance` 文件夹中创建 SQLite 数据库文件。

通过执行这些步骤，您应该能够在 PythonAnywhere 上成功运行您的 GOST 隧道管理器应用程序。请记住查阅 PythonAnywhere 帮助页面以获取有关特定功能的更多详细信息。
