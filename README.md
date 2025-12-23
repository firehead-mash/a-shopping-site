# Django 网上购物系统课程实验

## 一、基本信息

- 学号：202330451241  
- 姓名：刘祖明  
- 课程名称：Web 应用开发 
- 实验性质：课程综合实验  
- 项目部署网址：[myshop](http://20.243.177.76/)
- 注册账号密码**不要**使用**敏感信息**，网站属于实验性质，**安全等级很低**
---

## 二、项目简介

本项目基于 Django Web 框架实现了一个基础的网上购物系统。系统支持商品展示、购物车管理、订单处理以及后台管理等功能，整体采用 B/S 架构设计。  
前端使用 HTML 与 Bootstrap 进行页面布局，后端使用 Django 提供业务逻辑支持，数据库采用 SQLite。

本项目主要用于课程实验与功能验证，重点在于后端逻辑设计与系统结构实现。

---

## 三、项目整体结构说明

项目完整目录结构如下：

```
a-shopping-site/
├─ manage.py
├─ db.sqlite3
├─ shop/
│ ├─ settings.py
│ ├─ urls.py
│ ├─ wsgi.py
│ └─ pycache/
├─ store/
│ ├─ models.py
│ ├─ views.py
│ ├─ forms.py
│ ├─ urls.py
│ ├─ admin.py
│ ├─ migrations/
│ │ └─ pycache/
│ └─ pycache/
├─ templates/
│ └─ admin/
├─ static/
│ └─ css/
├─ media/
│ └─ products/
└─ requirements.txt
```

---

## 四、各模块功能说明

### 1. 根目录文件

- **manage.py**  
  Django 项目管理入口，用于启动服务器、执行数据库迁移等操作。

- **db.sqlite3**  
  SQLite 数据库文件，存储系统运行过程中产生的数据，如用户、商品、订单信息等。

- **requirements.txt**  
  项目依赖库列表，用于环境快速部署。

---

### 2. shop 目录（项目配置模块）

该目录用于 Django 项目的全局配置与部署相关设置。

- **settings.py**  
  项目核心配置文件，包含应用注册、数据库、静态文件等配置。

- **urls.py**  
  项目级路由配置文件，负责分发请求到各应用。

- **wsgi.py**  
  WSGI 接口文件，用于 Gunicorn 等服务器部署。

---

### 3. store 目录（核心业务模块）

该目录为系统主要业务逻辑实现部分。

- **models.py**  
  定义系统数据模型，包括商品、购物车、订单、订单明细等实体。

- **views.py**  
  实现主要业务逻辑，如商品浏览、加入购物车、下单、库存校验、订单管理等功能。

- **forms.py**  
  定义表单类，用于用户注册、登录、结算等操作。

- **urls.py**  
  应用级路由配置文件。

- **admin.py**  
  注册模型到 Django 后台管理系统，便于管理员维护数据。

- **migrations/**  
  数据库迁移文件目录，用于记录模型结构变化。

---

### 4. templates 目录（页面模板）

用于存放 HTML 模板文件，负责页面展示。

- **base.html**  
  网站基础模板，定义公共导航栏和整体页面布局。

- **templates/admin/**  
  后台管理相关页面模板，如订单管理和销售统计报表页面。

---

### 5. static 目录（静态资源）

- **static/css/**  
  留空文件。存放页面样式文件，用于页面样式调整。

---

### 6. media 目录（媒体资源）

- **media/products/**  
  存放商品图片文件，图片由管理员上传并用于商品展示。已经存放了部分示例图片

---

## 五、本地运行说明（简要）

1. 创建并激活 Python 虚拟环境  
2. 安装项目依赖：

   ```bash
   pip install -r requirements.txt
   ```

3. 执行数据库迁移：

   ```bash
   python manage.py migrate
   ```

4. 启动开发服务器：

   ```bash
   python manage.py runserver
   ```
