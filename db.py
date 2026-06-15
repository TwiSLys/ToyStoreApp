import os
import sqlite3
import sys
from contextlib import contextmanager


def application_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = application_dir()
DATABASE_PATH = os.path.join(APP_DIR, "database", "toy_store.db")


@contextmanager
def connect():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def fetch_all(query, parameters=()):
    with connect() as connection:
        return connection.execute(query, parameters).fetchall()


def fetch_one(query, parameters=()):
    with connect() as connection:
        return connection.execute(query, parameters).fetchone()


def execute(query, parameters=()):
    with connect() as connection:
        cursor = connection.execute(query, parameters)
        return cursor.lastrowid


def authenticate(login, password):
    return fetch_one(
        """
        SELECT users.id, users.full_name, users.login, roles.name AS role
        FROM users
        JOIN roles ON roles.id = users.role_id
        WHERE users.login = ? AND users.password = ?
        """,
        (login.strip(), password),
    )


def get_products(search="", supplier="Все поставщики", sort_mode="Без сортировки"):
    conditions = []
    parameters = []
    if search.strip():
        pattern = f"%{search.strip()}%"
        conditions.append(
            """
            (products.article LIKE ? OR products.name LIKE ?
             OR products.unit LIKE ? OR products.description LIKE ?
             OR categories.name LIKE ? OR suppliers.name LIKE ?
             OR manufacturers.name LIKE ?)
            """
        )
        parameters.extend([pattern] * 7)
    if supplier != "Все поставщики":
        conditions.append("suppliers.name = ?")
        parameters.append(supplier)

    order_by = {
        "Количество: по возрастанию": "products.stock ASC",
        "Количество: по убыванию": "products.stock DESC",
        "Цена: по возрастанию": "products.price ASC",
        "Цена: по убыванию": "products.price DESC",
    }.get(sort_mode, "products.id ASC")
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    return fetch_all(
        f"""
        SELECT products.*, categories.name AS category,
               suppliers.name AS supplier, manufacturers.name AS manufacturer
        FROM products
        JOIN categories ON categories.id = products.category_id
        JOIN suppliers ON suppliers.id = products.supplier_id
        JOIN manufacturers ON manufacturers.id = products.manufacturer_id
        {where_clause}
        ORDER BY {order_by}
        """,
        parameters,
    )


def get_product(product_id):
    return fetch_one(
        """
        SELECT products.*, categories.name AS category,
               suppliers.name AS supplier, manufacturers.name AS manufacturer
        FROM products
        JOIN categories ON categories.id = products.category_id
        JOIN suppliers ON suppliers.id = products.supplier_id
        JOIN manufacturers ON manufacturers.id = products.manufacturer_id
        WHERE products.id = ?
        """,
        (product_id,),
    )


def get_lookup(table_name):
    allowed = {"categories", "suppliers", "manufacturers", "pickup_points"}
    if table_name not in allowed:
        raise ValueError("Недопустимый справочник")
    column = "address" if table_name == "pickup_points" else "name"
    return fetch_all(f"SELECT id, {column} AS value FROM {table_name} ORDER BY {column}")


def add_lookup_value(connection, table_name, value):
    allowed = {"categories", "suppliers", "manufacturers"}
    if table_name not in allowed:
        raise ValueError("Недопустимый справочник")
    connection.execute(
        f"INSERT OR IGNORE INTO {table_name}(name) VALUES (?)", (value.strip(),)
    )
    return connection.execute(
        f"SELECT id FROM {table_name} WHERE name = ?", (value.strip(),)
    ).fetchone()[0]


def save_product(values, product_id=None):
    with connect() as connection:
        category_id = add_lookup_value(connection, "categories", values["category"])
        supplier_id = add_lookup_value(connection, "suppliers", values["supplier"])
        manufacturer_id = add_lookup_value(
            connection, "manufacturers", values["manufacturer"]
        )
        parameters = (
            values["article"],
            values["name"],
            values["unit"],
            values["price"],
            supplier_id,
            manufacturer_id,
            category_id,
            values["discount"],
            values["stock"],
            values["description"],
            values["image_path"],
        )
        if product_id is None:
            cursor = connection.execute(
                """
                INSERT INTO products(
                    article, name, unit, price, supplier_id, manufacturer_id,
                    category_id, discount, stock, description, image_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                parameters,
            )
            return cursor.lastrowid
        connection.execute(
            """
            UPDATE products
            SET article = ?, name = ?, unit = ?, price = ?, supplier_id = ?,
                manufacturer_id = ?, category_id = ?, discount = ?, stock = ?,
                description = ?, image_path = ?
            WHERE id = ?
            """,
            parameters + (product_id,),
        )
        return product_id


def delete_product(product_id):
    execute("DELETE FROM products WHERE id = ?", (product_id,))


def get_orders():
    return fetch_all(
        """
        SELECT orders.id, orders.order_date, orders.delivery_date, orders.status,
               orders.receive_code, pickup_points.address,
               COALESCE(users.full_name, 'Не указан') AS client,
               GROUP_CONCAT(products.article || ' x' || order_items.quantity, ', ')
                   AS items
        FROM orders
        JOIN pickup_points ON pickup_points.id = orders.pickup_point_id
        LEFT JOIN users ON users.id = orders.client_id
        LEFT JOIN order_items ON order_items.order_id = orders.id
        LEFT JOIN products ON products.id = order_items.product_id
        GROUP BY orders.id
        ORDER BY orders.id
        """
    )


def get_order(order_id):
    order = fetch_one(
        """
        SELECT orders.*, pickup_points.address,
               COALESCE(users.full_name, '') AS client
        FROM orders
        JOIN pickup_points ON pickup_points.id = orders.pickup_point_id
        LEFT JOIN users ON users.id = orders.client_id
        WHERE orders.id = ?
        """,
        (order_id,),
    )
    items = fetch_all(
        """
        SELECT products.article, order_items.quantity
        FROM order_items
        JOIN products ON products.id = order_items.product_id
        WHERE order_items.order_id = ?
        ORDER BY products.article
        """,
        (order_id,),
    )
    return order, items


def get_clients():
    return fetch_all(
        """
        SELECT users.id, users.full_name
        FROM users
        JOIN roles ON roles.id = users.role_id
        WHERE roles.name = 'Авторизированный клиент'
        ORDER BY users.full_name
        """
    )


def save_order(values, items, order_id=None):
    with connect() as connection:
        pickup_point_id = connection.execute(
            "SELECT id FROM pickup_points WHERE address = ?", (values["address"],)
        ).fetchone()
        if pickup_point_id is None:
            raise ValueError("Выберите существующий пункт выдачи")
        parameters = (
            values["order_date"],
            values["delivery_date"],
            pickup_point_id[0],
            values["client_id"],
            values["receive_code"],
            values["status"],
        )
        if order_id is None:
            cursor = connection.execute(
                """
                INSERT INTO orders(
                    order_date, delivery_date, pickup_point_id,
                    client_id, receive_code, status
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                parameters,
            )
            order_id = cursor.lastrowid
        else:
            connection.execute(
                """
                UPDATE orders
                SET order_date = ?, delivery_date = ?, pickup_point_id = ?,
                    client_id = ?, receive_code = ?, status = ?
                WHERE id = ?
                """,
                parameters + (order_id,),
            )
            connection.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
        for article, quantity in items:
            product = connection.execute(
                "SELECT id FROM products WHERE article = ?", (article,)
            ).fetchone()
            if product is None:
                raise ValueError(f"Товар с артикулом {article} не найден")
            connection.execute(
                """
                INSERT INTO order_items(order_id, product_id, quantity)
                VALUES (?, ?, ?)
                """,
                (order_id, product[0], quantity),
            )
        return order_id


def delete_order(order_id):
    execute("DELETE FROM orders WHERE id = ?", (order_id,))
