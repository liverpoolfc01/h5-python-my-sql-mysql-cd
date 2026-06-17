import os
from decimal import Decimal

import pymysql
from werkzeug.security import generate_password_hash


DB_HOST = os.getenv("DB_HOST", "cd-cdb-a197586k.sql.tencentcdb.com")
DB_PORT = int(os.getenv("DB_PORT", "63805"))
DB_USER = os.getenv("DB_USER", "test")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "codex_ecommerce_demo")


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
DB_HOST = os.getenv("DB_HOST", DB_HOST)
DB_PORT = int(os.getenv("DB_PORT", str(DB_PORT)))
DB_USER = os.getenv("DB_USER", DB_USER)
DB_PASSWORD = os.getenv("DB_PASSWORD", DB_PASSWORD)
DB_NAME = os.getenv("DB_NAME", DB_NAME)


def connect(database=None):
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(64) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        role ENUM('customer','merchant') NOT NULL DEFAULT 'customer',
        phone VARCHAR(32),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS products (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(120) NOT NULL,
        category VARCHAR(64) NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        stock INT NOT NULL DEFAULT 0,
        image_color VARCHAR(32) NOT NULL DEFAULT '#2f80ed',
        description TEXT,
        is_active TINYINT(1) NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS coupons (
        id INT AUTO_INCREMENT PRIMARY KEY,
        code VARCHAR(40) NOT NULL UNIQUE,
        title VARCHAR(120) NOT NULL,
        discount_type ENUM('amount','percent') NOT NULL DEFAULT 'amount',
        discount_value DECIMAL(10,2) NOT NULL,
        min_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
        total INT NOT NULL DEFAULT 0,
        claimed INT NOT NULL DEFAULT 0,
        starts_at DATETIME NOT NULL,
        ends_at DATETIME NOT NULL,
        is_active TINYINT(1) NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS user_coupons (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        coupon_id INT NOT NULL,
        used_at DATETIME,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uniq_user_coupon (user_id, coupon_id),
        CONSTRAINT fk_user_coupons_user FOREIGN KEY (user_id) REFERENCES users(id),
        CONSTRAINT fk_user_coupons_coupon FOREIGN KEY (coupon_id) REFERENCES coupons(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        order_no VARCHAR(40) NOT NULL UNIQUE,
        user_id INT NOT NULL,
        coupon_id INT,
        status ENUM('pending','paid','shipped','finished','cancelled') NOT NULL DEFAULT 'pending',
        receiver_name VARCHAR(80) NOT NULL,
        receiver_phone VARCHAR(32) NOT NULL,
        receiver_address VARCHAR(255) NOT NULL,
        total_amount DECIMAL(10,2) NOT NULL,
        discount_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
        payable_amount DECIMAL(10,2) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users(id),
        CONSTRAINT fk_orders_coupon FOREIGN KEY (coupon_id) REFERENCES coupons(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS order_items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        order_id INT NOT NULL,
        product_id INT NOT NULL,
        product_name VARCHAR(120) NOT NULL,
        unit_price DECIMAL(10,2) NOT NULL,
        quantity INT NOT NULL,
        subtotal DECIMAL(10,2) NOT NULL,
        CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders(id),
        CONSTRAINT fk_order_items_product FOREIGN KEY (product_id) REFERENCES products(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS group_buys (
        id INT AUTO_INCREMENT PRIMARY KEY,
        product_id INT NOT NULL,
        title VARCHAR(120) NOT NULL,
        group_price DECIMAL(10,2) NOT NULL,
        required_members INT NOT NULL DEFAULT 3,
        current_members INT NOT NULL DEFAULT 0,
        starts_at DATETIME NOT NULL,
        ends_at DATETIME NOT NULL,
        is_active TINYINT(1) NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_group_buys_product FOREIGN KEY (product_id) REFERENCES products(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS group_buy_members (
        id INT AUTO_INCREMENT PRIMARY KEY,
        group_buy_id INT NOT NULL,
        user_id INT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uniq_group_member (group_buy_id, user_id),
        CONSTRAINT fk_group_members_group FOREIGN KEY (group_buy_id) REFERENCES group_buys(id),
        CONSTRAINT fk_group_members_user FOREIGN KEY (user_id) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS lotteries (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(120) NOT NULL,
        starts_at DATETIME NOT NULL,
        ends_at DATETIME NOT NULL,
        is_active TINYINT(1) NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS lottery_prizes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        lottery_id INT NOT NULL,
        name VARCHAR(120) NOT NULL,
        quantity INT NOT NULL DEFAULT 0,
        probability DECIMAL(6,4) NOT NULL DEFAULT 0,
        CONSTRAINT fk_lottery_prizes_lottery FOREIGN KEY (lottery_id) REFERENCES lotteries(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS lottery_entries (
        id INT AUTO_INCREMENT PRIMARY KEY,
        lottery_id INT NOT NULL,
        user_id INT NOT NULL,
        prize_id INT,
        result VARCHAR(120) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_lottery_entries_lottery FOREIGN KEY (lottery_id) REFERENCES lotteries(id),
        CONSTRAINT fk_lottery_entries_user FOREIGN KEY (user_id) REFERENCES users(id),
        CONSTRAINT fk_lottery_entries_prize FOREIGN KEY (prize_id) REFERENCES lottery_prizes(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]


PRODUCTS = [
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


def seed_user(cur, username, password, role):
    cur.execute("SELECT id FROM users WHERE username=%s", (username,))
    if cur.fetchone():
        return
    cur.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
        (username, generate_password_hash(password), role),
    )


def main():
    root = connect()
    with root.cursor() as cur:
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    root.commit()
    root.close()

    conn = connect(DB_NAME)
    with conn.cursor() as cur:
        for sql in SCHEMA:
            cur.execute(sql)

        seed_user(cur, "admin", "test1234", "merchant")
        seed_user(cur, "test", "test1234", "customer")

        cur.execute("SELECT COUNT(*) AS c FROM products")
        if cur.fetchone()["c"] == 0:
            cur.executemany(
                """
                INSERT INTO products
                (name, category, price, stock, image_color, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                PRODUCTS,
            )

        cur.execute("SELECT COUNT(*) AS c FROM coupons")
        if cur.fetchone()["c"] == 0:
            cur.executemany(
                """
                INSERT INTO coupons
                (code, title, discount_type, discount_value, min_amount, total, starts_at, ends_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), DATE_ADD(NOW(), INTERVAL 90 DAY))
                """,
                [
                    ("WELCOME20", "新人立减 20 元", "amount", Decimal("20"), Decimal("99"), 500),
                    ("VIP85", "全场 85 折券", "percent", Decimal("0.85"), Decimal("199"), 200),
                ],
            )

        cur.execute("SELECT id FROM products ORDER BY id LIMIT 2")
        product_ids = [row["id"] for row in cur.fetchall()]
        cur.execute("SELECT COUNT(*) AS c FROM group_buys")
        if product_ids and cur.fetchone()["c"] == 0:
            cur.executemany(
                """
                INSERT INTO group_buys
                (product_id, title, group_price, required_members, starts_at, ends_at)
                VALUES (%s, %s, %s, %s, NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY))
                """,
                [
                    (product_ids[0], "云感针织衫 3 人拼团", Decimal("99"), 3),
                    (product_ids[1], "轻跑运动鞋 5 人拼团", Decimal("219"), 5),
                ],
            )

        cur.execute("SELECT COUNT(*) AS c FROM lotteries")
        if cur.fetchone()["c"] == 0:
            cur.execute(
                "INSERT INTO lotteries (title, starts_at, ends_at) VALUES (%s, NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY))",
                ("618 幸运抽奖",),
            )
            lottery_id = cur.lastrowid
            cur.executemany(
                """
                INSERT INTO lottery_prizes (lottery_id, name, quantity, probability)
                VALUES (%s, %s, %s, %s)
                """,
                [
                    (lottery_id, "满 99 减 30 优惠券", 50, Decimal("0.1200")),
                    (lottery_id, "便携保温杯", 10, Decimal("0.0300")),
                    (lottery_id, "谢谢参与", 9999, Decimal("0.8500")),
                ],
            )
    conn.commit()
    conn.close()
    print(f"Database ready: {DB_NAME}")


if __name__ == "__main__":
    main()
