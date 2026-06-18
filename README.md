# 云栈优选电商网站

Python + MySQL 的电商原型，包含用户 H5 商城、商家后台、下单、商品添加、优惠券、拼团和抽奖。

## 已初始化

- 数据库：`codex_ecommerce_demo`
- 云数据库：腾讯云 MySQL `cd-cdb-a197586k.sql.tencentcdb.com:63805`
- 商家后台账号：`admin` / `test1234`
- 用户账号：`test` / `test1234`
- 默认商品：20 个

## 启动

```bash
.venv/bin/python app.py
```

打开：

```text
http://127.0.0.1:5000/
```

## 常用入口

- 用户 H5 商城：`/`
- 用户订单：`/orders`
- 商家后台：`/admin`
- 添加商品：`/admin/products/new`
- 营销活动：`/admin/marketing`

## 重新初始化数据库

```bash
.venv/bin/python init_db.py
```

可以通过环境变量覆盖数据库配置：

```bash
DB_HOST=127.0.0.1 DB_PORT=3306 DB_USER=root DB_PASSWORD=xxx DB_NAME=codex_ecommerce_demo .venv/bin/python init_db.py
```

## Render 免费部署

项目已包含 `render.yaml`，可以在 Render 导入 GitHub 仓库后创建免费 Web Service。创建时选择 Singapore 区域，并填写以下环境变量：

- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`

启动命令：

```bash
gunicorn app:app
```
