import os
import random
import time
from contextlib import contextmanager
from decimal import Decimal

import pymysql
from flask import Flask, flash, g, has_request_context, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash


def load_dotenv(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "cd-cdb-a197586k.sql.tencentcdb.com"),
    "port": int(os.getenv("DB_PORT", "63805")),
    "user": os.getenv("DB_USER", "test"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "codex_ecommerce_demo"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "3")),
    "read_timeout": int(os.getenv("DB_READ_TIMEOUT", "5")),
    "write_timeout": int(os.getenv("DB_WRITE_TIMEOUT", "5")),
}

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "codex-ecommerce-dev-secret")
HOME_CACHE = {"expires_at": 0, "data": None}
HOME_CACHE_TTL = int(os.getenv("HOME_CACHE_TTL", "60"))

FALLBACK_PRODUCTS = [
    ("云感针织衫", "女装", "129.00", 220, "#d85c5c", "柔软亲肤，适合通勤与日常搭配。"),
    ("轻跑运动鞋", "鞋包", "269.00", 180, "#2864c8", "缓震鞋底，适合城市慢跑。"),
    ("陶瓷马克杯", "家居", "39.90", 360, "#f2a03d", "高温烧制，早餐咖啡都顺手。"),
    ("无线蓝牙耳机", "数码", "199.00", 145, "#1f9d89", "低延迟连接，通勤听歌清晰稳定。"),
    ("儿童绘本套装", "母婴", "88.00", 90, "#8e6bd8", "精选启蒙故事，亲子阅读更轻松。"),
    ("低脂燕麦礼盒", "食品", "69.00", 260, "#b67b43", "早餐代餐，搭配牛奶口感更佳。"),
    ("便携保温杯", "户外", "79.00", 310, "#2c8c70", "长效保温，车载和露营都适用。"),
    ("护眼台灯", "家居", "159.00", 128, "#e0b531", "三档调光，学习办公不刺眼。"),
    ("真皮双肩包", "鞋包", "329.00", 65, "#4b5563", "大容量分区，短途出行好整理。"),
    ("空气炸锅", "家电", "399.00", 74, "#c75d7b", "少油烹饪，薯条鸡翅都方便。"),
    ("玻璃收纳罐", "家居", "49.90", 430, "#7aa95c", "密封防潮，厨房收纳更整洁。"),
    ("男士休闲衬衫", "男装", "119.00", 205, "#5572a7", "挺括版型，单穿内搭都合适。"),
    ("维生素软糖", "健康", "59.00", 188, "#dc7a45", "每日营养补充，水果风味。"),
    ("智能体脂秤", "数码", "149.00", 133, "#5d8ca8", "多项身体数据，家庭健康管理。"),
    ("香薰蜡烛", "美妆", "69.90", 240, "#b56aa1", "舒缓香调，适合睡前放松。"),
    ("折叠露营椅", "户外", "139.00", 96, "#56834c", "稳固轻便，收纳不占空间。"),
    ("宠物自动饮水机", "宠物", "129.00", 112, "#5096b3", "循环活水，容量适合猫咪小犬。"),
    ("有机洗发水", "美妆", "89.00", 173, "#3b9c75", "温和清洁，清爽不厚重。"),
    ("积木创意套装", "玩具", "109.00", 84, "#d04747", "开放式拼搭，训练空间想象。"),
    ("轻薄防晒衣", "服饰", "99.00", 265, "#5c80c9", "UPF 防晒，夏季户外必备。"),
]


def get_request_db():
    if not has_request_context():
        return None
    if "db_conn" not in g:
        g.db_conn = pymysql.connect(**DB_CONFIG)
    return g.db_conn


@app.teardown_appcontext
def close_request_db(error=None):
    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()


@contextmanager
def db():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query_all(sql, params=()):
    conn = get_request_db()
    if conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def query_one(sql, params=()):
    conn = get_request_db()
    if conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def login_required(role=None):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                flash("请先登录")
                return redirect(url_for("login", next=request.path))
            if role and session.get("role") != role:
                flash("没有访问权限")
                return redirect(url_for("home"))
            return fn(*args, **kwargs)

        wrapper.__name__ = fn.__name__
        return wrapper

    return decorator


def calc_discount(total, coupon):
    if not coupon:
        return Decimal("0.00")
    total = Decimal(str(total))
    if total < Decimal(str(coupon["min_amount"])):
        return Decimal("0.00")
    if coupon["discount_type"] == "percent":
        return (total - total * Decimal(str(coupon["discount_value"]))).quantize(Decimal("0.01"))
    return min(total, Decimal(str(coupon["discount_value"]))).quantize(Decimal("0.01"))


def fallback_home_data():
    products = [
        {
            "id": index,
            "name": name,
            "category": category,
            "price": Decimal(price),
            "stock": stock,
            "image_color": color,
            "description": description,
        }
        for index, (name, category, price, stock, color, description) in enumerate(FALLBACK_PRODUCTS, start=1)
    ]
    categories = [{"category": item["category"]} for item in products]
    unique_categories = {item["category"]: item for item in categories}
    coupons = [
        {"id": 1, "title": "新人立减 20 元", "min_amount": Decimal("99.00"), "total": 500, "claimed": 0},
        {"id": 2, "title": "全场 85 折券", "min_amount": Decimal("199.00"), "total": 200, "claimed": 0},
    ]
    groups = [
        {
            "id": 1,
            "title": "云感针织衫 3 人拼团",
            "product_name": "云感针织衫",
            "group_price": Decimal("99.00"),
            "current_members": 0,
            "required_members": 3,
            "image_color": "#d85c5c",
        },
        {
            "id": 2,
            "title": "轻跑运动鞋 5 人拼团",
            "product_name": "轻跑运动鞋",
            "group_price": Decimal("219.00"),
            "current_members": 0,
            "required_members": 5,
            "image_color": "#2864c8",
        },
    ]
    lottery = {"id": 1, "title": "618 幸运抽奖"}
    return products, list(unique_categories.values()), coupons, groups, lottery


def get_home_data():
    now = time.time()
    if HOME_CACHE["data"] and HOME_CACHE["expires_at"] > now:
        return HOME_CACHE["data"]

    try:
        products = query_all("SELECT * FROM products WHERE is_active=1 ORDER BY id DESC")
        categories = query_all("SELECT DISTINCT category FROM products WHERE is_active=1 ORDER BY category")
        coupons = query_all(
            """
            SELECT * FROM coupons
            WHERE is_active=1 AND starts_at <= NOW() AND ends_at >= NOW() AND claimed < total
            ORDER BY id DESC LIMIT 4
            """
        )
        groups = query_all(
            """
            SELECT gb.*, p.name AS product_name, p.image_color
            FROM group_buys gb JOIN products p ON p.id=gb.product_id
            WHERE gb.is_active=1 AND gb.ends_at >= NOW()
            ORDER BY gb.id DESC LIMIT 3
            """
        )
        lottery = query_one("SELECT * FROM lotteries WHERE is_active=1 AND ends_at >= NOW() ORDER BY id DESC LIMIT 1")
        data = (products, categories, coupons, groups, lottery)
    except pymysql.MySQLError:
        data = fallback_home_data()
        flash("云数据库连接较慢，当前先展示演示数据")

    HOME_CACHE["data"] = data
    HOME_CACHE["expires_at"] = now + HOME_CACHE_TTL
    return data


@app.context_processor
def inject_user():
    return {"current_user": {"id": session.get("user_id"), "username": session.get("username"), "role": session.get("role")}}


@app.route("/")
def home():
    keyword = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    products, categories, coupons, groups, lottery = get_home_data()
    if keyword:
        products = [p for p in products if keyword in p["name"] or keyword in p["description"]]
    if category:
        products = [p for p in products if p["category"] == category]
    return render_template("home.html", products=products, categories=categories, coupons=coupons, groups=groups, lottery=lottery)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        try:
            user = query_one("SELECT * FROM users WHERE username=%s", (username,))
        except pymysql.MySQLError:
            user = None
            flash("云数据库连接超时，请稍后再登录")
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash("登录成功")
            next_url = request.args.get("next")
            if user["role"] == "merchant" and not next_url:
                return redirect(url_for("admin_dashboard"))
            return redirect(next_url or url_for("home"))
        flash("用户名或密码错误")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("已退出登录")
    return redirect(url_for("home"))


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    try:
        product = query_one("SELECT * FROM products WHERE id=%s AND is_active=1", (product_id,))
    except pymysql.MySQLError:
        products, categories, coupons, groups, lottery = fallback_home_data()
        product = next((item for item in products if item["id"] == product_id), None)
        product_groups = [group for group in groups if product and group["product_name"] == product["name"]]
        if product:
            flash("云数据库连接较慢，当前先展示演示商品")
            return render_template("product.html", product=product, coupons=coupons, groups=product_groups)
    if not product:
        flash("商品不存在")
        return redirect(url_for("home"))
    coupons = query_all(
        """
        SELECT * FROM coupons
        WHERE is_active=1 AND starts_at <= NOW() AND ends_at >= NOW() AND claimed < total
        ORDER BY min_amount
        """
    )
    groups = query_all(
        """
        SELECT * FROM group_buys
        WHERE product_id=%s AND is_active=1 AND ends_at >= NOW()
        ORDER BY id DESC
        """,
        (product_id,),
    )
    return render_template("product.html", product=product, coupons=coupons, groups=groups)


@app.route("/coupon/<int:coupon_id>/claim", methods=["POST"])
@login_required("customer")
def claim_coupon(coupon_id):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM coupons WHERE id=%s AND is_active=1 AND starts_at <= NOW() AND ends_at >= NOW() FOR UPDATE",
                (coupon_id,),
            )
            coupon = cur.fetchone()
            if not coupon or coupon["claimed"] >= coupon["total"]:
                flash("优惠券已领完或已过期")
                return redirect(request.referrer or url_for("home"))
            try:
                cur.execute(
                    "INSERT INTO user_coupons (user_id, coupon_id) VALUES (%s, %s)",
                    (session["user_id"], coupon_id),
                )
                cur.execute("UPDATE coupons SET claimed=claimed+1 WHERE id=%s", (coupon_id,))
                flash("领取成功")
            except pymysql.err.IntegrityError:
                flash("你已经领取过这张优惠券")
    return redirect(request.referrer or url_for("home"))


@app.route("/order/create", methods=["POST"])
@login_required("customer")
def create_order():
    product_id = int(request.form["product_id"])
    quantity = max(1, int(request.form.get("quantity", 1)))
    coupon_id = request.form.get("coupon_id") or None
    receiver_name = request.form["receiver_name"].strip()
    receiver_phone = request.form["receiver_phone"].strip()
    receiver_address = request.form["receiver_address"].strip()

    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM products WHERE id=%s AND is_active=1 FOR UPDATE", (product_id,))
            product = cur.fetchone()
            if not product or product["stock"] < quantity:
                flash("库存不足")
                return redirect(url_for("product_detail", product_id=product_id))

            coupon = None
            if coupon_id:
                cur.execute(
                    """
                    SELECT c.* FROM user_coupons uc JOIN coupons c ON c.id=uc.coupon_id
                    WHERE uc.user_id=%s AND c.id=%s AND uc.used_at IS NULL
                    AND c.is_active=1 AND c.starts_at <= NOW() AND c.ends_at >= NOW()
                    """,
                    (session["user_id"], coupon_id),
                )
                coupon = cur.fetchone()

            total = Decimal(str(product["price"])) * quantity
            discount = calc_discount(total, coupon)
            payable = (total - discount).quantize(Decimal("0.01"))
            order_no = f"NO{int(time.time())}{random.randint(1000, 9999)}"
            cur.execute(
                """
                INSERT INTO orders
                (order_no, user_id, coupon_id, receiver_name, receiver_phone, receiver_address,
                 total_amount, discount_amount, payable_amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (order_no, session["user_id"], coupon_id, receiver_name, receiver_phone, receiver_address, total, discount, payable),
            )
            order_id = cur.lastrowid
            cur.execute(
                """
                INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, subtotal)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (order_id, product_id, product["name"], product["price"], quantity, total),
            )
            cur.execute("UPDATE products SET stock=stock-%s WHERE id=%s", (quantity, product_id))
            if coupon:
                cur.execute("UPDATE user_coupons SET used_at=NOW() WHERE user_id=%s AND coupon_id=%s", (session["user_id"], coupon_id))
    flash(f"下单成功，应付 ¥{payable}")
    return redirect(url_for("my_orders"))


@app.route("/orders")
@login_required("customer")
def my_orders():
    orders = query_all(
        """
        SELECT o.*, GROUP_CONCAT(CONCAT(oi.product_name, ' x', oi.quantity) SEPARATOR '，') AS items
        FROM orders o JOIN order_items oi ON oi.order_id=o.id
        WHERE o.user_id=%s
        GROUP BY o.id
        ORDER BY o.id DESC
        """,
        (session["user_id"],),
    )
    coupons = query_all(
        """
        SELECT c.*, uc.used_at FROM user_coupons uc JOIN coupons c ON c.id=uc.coupon_id
        WHERE uc.user_id=%s ORDER BY uc.id DESC
        """,
        (session["user_id"],),
    )
    return render_template("orders.html", orders=orders, coupons=coupons)


@app.route("/group/<int:group_id>/join", methods=["POST"])
@login_required("customer")
def join_group(group_id):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM group_buys WHERE id=%s AND is_active=1 AND ends_at >= NOW() FOR UPDATE", (group_id,))
            group = cur.fetchone()
            if not group:
                flash("拼团不存在或已结束")
                return redirect(url_for("home"))
            try:
                cur.execute("INSERT INTO group_buy_members (group_buy_id, user_id) VALUES (%s, %s)", (group_id, session["user_id"]))
                cur.execute("UPDATE group_buys SET current_members=current_members+1 WHERE id=%s", (group_id,))
                flash("参团成功")
            except pymysql.err.IntegrityError:
                flash("你已经参加过这个拼团")
    return redirect(request.referrer or url_for("home"))


@app.route("/lottery/<int:lottery_id>/draw", methods=["POST"])
@login_required("customer")
def draw_lottery(lottery_id):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM lotteries WHERE id=%s AND is_active=1 AND ends_at >= NOW()", (lottery_id,))
            lottery = cur.fetchone()
            if not lottery:
                flash("抽奖活动已结束")
                return redirect(url_for("home"))
            cur.execute("SELECT * FROM lottery_prizes WHERE lottery_id=%s ORDER BY id", (lottery_id,))
            prizes = cur.fetchall()
            roll = random.random()
            acc = 0
            selected = None
            for prize in prizes:
                acc += float(prize["probability"])
                if roll <= acc and prize["quantity"] > 0:
                    selected = prize
                    break
            if not selected:
                selected = {"id": None, "name": "谢谢参与"}
            if selected.get("id"):
                cur.execute("UPDATE lottery_prizes SET quantity=quantity-1 WHERE id=%s AND quantity>0", (selected["id"],))
            cur.execute(
                "INSERT INTO lottery_entries (lottery_id, user_id, prize_id, result) VALUES (%s, %s, %s, %s)",
                (lottery_id, session["user_id"], selected.get("id"), selected["name"]),
            )
            flash(f"抽奖结果：{selected['name']}")
    return redirect(url_for("home"))


@app.route("/admin")
@login_required("merchant")
def admin_dashboard():
    stats = {
        "products": query_one("SELECT COUNT(*) AS c FROM products")["c"],
        "orders": query_one("SELECT COUNT(*) AS c FROM orders")["c"],
        "sales": query_one("SELECT COALESCE(SUM(payable_amount),0) AS c FROM orders")["c"],
        "customers": query_one("SELECT COUNT(*) AS c FROM users WHERE role='customer'")["c"],
    }
    products = query_all("SELECT * FROM products ORDER BY id DESC LIMIT 20")
    orders = query_all(
        """
        SELECT o.*, u.username, GROUP_CONCAT(CONCAT(oi.product_name, ' x', oi.quantity) SEPARATOR '，') AS items
        FROM orders o JOIN users u ON u.id=o.user_id JOIN order_items oi ON oi.order_id=o.id
        GROUP BY o.id ORDER BY o.id DESC LIMIT 20
        """
    )
    return render_template("admin/dashboard.html", stats=stats, products=products, orders=orders)


@app.route("/admin/products/new", methods=["GET", "POST"])
@login_required("merchant")
def admin_product_new():
    if request.method == "POST":
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO products (name, category, price, stock, image_color, description)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        request.form["name"].strip(),
                        request.form["category"].strip(),
                        request.form["price"],
                        request.form["stock"],
                        request.form.get("image_color") or "#2f80ed",
                        request.form["description"].strip(),
                    ),
                )
        flash("商品添加成功")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin/product_form.html")


@app.route("/admin/marketing", methods=["GET", "POST"])
@login_required("merchant")
def admin_marketing():
    if request.method == "POST":
        kind = request.form["kind"]
        with db() as conn:
            with conn.cursor() as cur:
                if kind == "coupon":
                    cur.execute(
                        """
                        INSERT INTO coupons
                        (code, title, discount_type, discount_value, min_amount, total, starts_at, ends_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW(), DATE_ADD(NOW(), INTERVAL %s DAY))
                        """,
                        (
                            request.form["code"].strip().upper(),
                            request.form["title"].strip(),
                            request.form["discount_type"],
                            request.form["discount_value"],
                            request.form["min_amount"],
                            request.form["total"],
                            request.form["days"],
                        ),
                    )
                    flash("优惠券创建成功")
                elif kind == "group":
                    cur.execute(
                        """
                        INSERT INTO group_buys
                        (product_id, title, group_price, required_members, starts_at, ends_at)
                        VALUES (%s, %s, %s, %s, NOW(), DATE_ADD(NOW(), INTERVAL %s DAY))
                        """,
                        (
                            request.form["product_id"],
                            request.form["title"].strip(),
                            request.form["group_price"],
                            request.form["required_members"],
                            request.form["days"],
                        ),
                    )
                    flash("拼团创建成功")
                elif kind == "lottery":
                    cur.execute(
                        "INSERT INTO lotteries (title, starts_at, ends_at) VALUES (%s, NOW(), DATE_ADD(NOW(), INTERVAL %s DAY))",
                        (request.form["title"].strip(), request.form["days"]),
                    )
                    lottery_id = cur.lastrowid
                    cur.execute(
                        "INSERT INTO lottery_prizes (lottery_id, name, quantity, probability) VALUES (%s, %s, %s, %s)",
                        (lottery_id, request.form["prize_name"].strip(), request.form["quantity"], request.form["probability"]),
                    )
                    cur.execute(
                        "INSERT INTO lottery_prizes (lottery_id, name, quantity, probability) VALUES (%s, '谢谢参与', 9999, %s)",
                        (lottery_id, max(0, 1 - float(request.form["probability"]))),
                    )
                    flash("抽奖活动创建成功")
        return redirect(url_for("admin_marketing"))

    products = query_all("SELECT id, name FROM products WHERE is_active=1 ORDER BY id DESC")
    coupons = query_all("SELECT * FROM coupons ORDER BY id DESC")
    groups = query_all(
        "SELECT gb.*, p.name AS product_name FROM group_buys gb JOIN products p ON p.id=gb.product_id ORDER BY gb.id DESC"
    )
    lotteries = query_all("SELECT * FROM lotteries ORDER BY id DESC")
    return render_template("admin/marketing.html", products=products, coupons=coupons, groups=groups, lotteries=lotteries)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
