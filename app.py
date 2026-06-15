import os
import shutil
import sqlite3
import uuid
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

import db


WHITE = "#FFFFFF"
SECONDARY = "#F5DEB3"
ACCENT = "#DEB887"
DISCOUNT_BACKGROUND = "#FFDEAD"
OUT_OF_STOCK_BACKGROUND = "#ADD8E6"
FONT = "Arial"


def asset_path(*parts):
    return os.path.join(db.APP_DIR, "assets", *parts)


def center_window(window, width, height):
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = max((screen_width - width) // 2, 0)
    y = max((screen_height - height) // 2, 0)
    window.geometry(f"{width}x{height}+{x}+{y}")


def load_photo(path, size):
    full_path = path if os.path.isabs(path) else os.path.join(db.APP_DIR, path)
    if not os.path.exists(full_path):
        full_path = asset_path("images", "picture.png")
    try:
        image = Image.open(full_path)
        image.thumbnail(size, Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", size, WHITE)
        offset = ((size[0] - image.width) // 2, (size[1] - image.height) // 2)
        if image.mode == "RGBA":
            canvas.paste(image, offset, image)
        else:
            canvas.paste(image.convert("RGB"), offset)
        return ImageTk.PhotoImage(canvas)
    except Exception:
        return None


class ToyStoreApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ООО «МирИгрушек» — Вход")
        self.configure(bg=WHITE)
        self.minsize(1000, 700)
        self.current_user = None
        self.current_frame = None
        self.product_editor = None
        self.order_editor = None
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure(".", font=(FONT, 10))
        self.style.configure("TButton", padding=7, background=ACCENT)
        self.style.map("TButton", background=[("active", SECONDARY)])
        self.style.configure("TCombobox", padding=4)
        icon = asset_path("icon.ico")
        if os.path.exists(icon):
            try:
                self.iconbitmap(icon)
            except tk.TclError:
                pass
        self.bind_all("<KeyPress>", self.handle_clipboard_shortcuts, add="+")
        center_window(self, 1180, 780)
        self.show_login()

    def handle_clipboard_shortcuts(self, event):
        if not event.state & 0x0004:
            return None
        widget = event.widget
        if not isinstance(widget, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox)):
            return None
        actions = {
            65: "<<SelectAll>>",
            67: "<<Copy>>",
            86: "<<Paste>>",
            88: "<<Cut>>",
        }
        virtual_event = actions.get(event.keycode)
        if virtual_event is None:
            return None
        if virtual_event == "<<SelectAll>>":
            if isinstance(widget, tk.Text):
                widget.tag_add("sel", "1.0", "end-1c")
                widget.mark_set("insert", "1.0")
                widget.see("insert")
            else:
                widget.selection_range(0, "end")
                widget.icursor("end")
        else:
            widget.event_generate(virtual_event)
        return "break"

    def set_frame(self, frame_class, *args):
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = frame_class(self, *args)
        self.current_frame.pack(fill="both", expand=True)

    def show_login(self):
        self.current_user = None
        self.title("ООО «МирИгрушек» — Вход")
        self.set_frame(LoginFrame)

    def show_products(self, user=None):
        self.current_user = user
        self.title("ООО «МирИгрушек» — Товары")
        self.set_frame(ProductListFrame)

    def show_orders(self):
        self.title("ООО «МирИгрушек» — Заказы")
        self.set_frame(OrderListFrame)

    def open_product_editor(self, product_id=None):
        if self.product_editor and self.product_editor.winfo_exists():
            self.product_editor.lift()
            self.product_editor.focus_force()
            return
        self.product_editor = ProductEditor(self, product_id)

    def open_order_editor(self, order_id=None):
        if self.order_editor and self.order_editor.winfo_exists():
            self.order_editor.lift()
            self.order_editor.focus_force()
            return
        self.order_editor = OrderEditor(self, order_id)


class Header(tk.Frame):
    def __init__(self, parent, title, show_back=False):
        super().__init__(parent, bg=SECONDARY, padx=18, pady=10)
        logo = load_photo(os.path.join("assets", "logo.png"), (72, 58))
        logo_label = tk.Label(self, bg=SECONDARY, image=logo)
        logo_label.image = logo
        logo_label.pack(side="left", padx=(0, 14))
        tk.Label(
            self,
            text=title,
            bg=SECONDARY,
            fg="#2B2118",
            font=(FONT, 18, "bold"),
        ).pack(side="left")
        if show_back:
            ttk.Button(self, text="Назад", command=parent.master.show_products).pack(
                side="right", padx=(10, 0)
            )
        ttk.Button(self, text="Выйти", command=parent.master.show_login).pack(
            side="right", padx=(10, 0)
        )
        user_name = (
            parent.master.current_user["full_name"]
            if parent.master.current_user
            else "Гость"
        )
        tk.Label(
            self,
            text=user_name,
            bg=SECONDARY,
            font=(FONT, 10, "bold"),
        ).pack(side="right", padx=12)


class LoginFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=WHITE)
        panel = tk.Frame(self, bg=SECONDARY, padx=42, pady=34)
        panel.place(relx=0.5, rely=0.5, anchor="center")
        logo = load_photo(os.path.join("assets", "logo.png"), (150, 115))
        logo_label = tk.Label(panel, image=logo, bg=SECONDARY)
        logo_label.image = logo
        logo_label.pack(pady=(0, 8))
        tk.Label(
            panel,
            text="ООО «МирИгрушек»",
            bg=SECONDARY,
            font=(FONT, 20, "bold"),
        ).pack()
        tk.Label(
            panel,
            text="Вход в информационную систему",
            bg=SECONDARY,
            font=(FONT, 12),
        ).pack(pady=(2, 20))

        form = tk.Frame(panel, bg=SECONDARY)
        form.pack(fill="x")
        tk.Label(form, text="Логин", bg=SECONDARY, anchor="w").pack(fill="x")
        self.login_entry = ttk.Entry(form, width=42)
        self.login_entry.pack(fill="x", pady=(3, 12))
        tk.Label(form, text="Пароль", bg=SECONDARY, anchor="w").pack(fill="x")
        self.password_entry = ttk.Entry(form, width=42, show="*")
        self.password_entry.pack(fill="x", pady=(3, 18))
        self.password_entry.bind("<Return>", lambda _event: self.login())
        ttk.Button(form, text="Войти", command=self.login).pack(fill="x")
        ttk.Button(
            form,
            text="Продолжить как гость",
            command=lambda: master.show_products(None),
        ).pack(fill="x", pady=(9, 0))
        self.login_entry.focus_set()

    def login(self):
        login = self.login_entry.get().strip()
        password = self.password_entry.get()
        if not login or not password:
            messagebox.showwarning(
                "Не заполнены поля",
                "Введите логин и пароль. Оба поля обязательны для авторизации.",
                parent=self,
            )
            return
        try:
            user = db.authenticate(login, password)
        except sqlite3.Error as error:
            messagebox.showerror(
                "Ошибка базы данных",
                f"Не удалось выполнить авторизацию.\n\n{error}",
                parent=self,
            )
            return
        if user is None:
            messagebox.showerror(
                "Ошибка авторизации",
                "Пользователь с указанными логином и паролем не найден.\n"
                "Проверьте раскладку клавиатуры и повторите ввод.",
                parent=self,
            )
            return
        self.master.show_products(user)


class ProductListFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=WHITE)
        self.role = master.current_user["role"] if master.current_user else "Гость"
        Header(self, "Каталог товаров").pack(fill="x")

        navigation = tk.Frame(self, bg=WHITE, padx=18, pady=10)
        navigation.pack(fill="x")
        if self.role in ("Менеджер", "Администратор"):
            ttk.Button(
                navigation, text="Заказы", command=master.show_orders
            ).pack(side="left")
        if self.role == "Администратор":
            ttk.Button(
                navigation,
                text="Добавить товар",
                command=lambda: master.open_product_editor(),
            ).pack(side="left", padx=8)

        self.search_var = tk.StringVar()
        self.supplier_var = tk.StringVar(value="Все поставщики")
        self.sort_var = tk.StringVar(value="Без сортировки")
        if self.role in ("Менеджер", "Администратор"):
            controls = tk.Frame(self, bg=SECONDARY, padx=18, pady=10)
            controls.pack(fill="x", padx=18, pady=(0, 8))
            tk.Label(controls, text="Поиск:", bg=SECONDARY).grid(row=0, column=0)
            ttk.Entry(controls, textvariable=self.search_var, width=36).grid(
                row=0, column=1, padx=(5, 14)
            )
            tk.Label(controls, text="Поставщик:", bg=SECONDARY).grid(row=0, column=2)
            suppliers = ["Все поставщики"] + [
                row["value"] for row in db.get_lookup("suppliers")
            ]
            ttk.Combobox(
                controls,
                textvariable=self.supplier_var,
                values=suppliers,
                state="readonly",
                width=20,
            ).grid(row=0, column=3, padx=(5, 14))
            tk.Label(controls, text="Сортировка:", bg=SECONDARY).grid(row=0, column=4)
            ttk.Combobox(
                controls,
                textvariable=self.sort_var,
                values=[
                    "Без сортировки",
                    "Количество: по возрастанию",
                    "Количество: по убыванию",
                    "Цена: по возрастанию",
                    "Цена: по убыванию",
                ],
                state="readonly",
                width=27,
            ).grid(row=0, column=5, padx=(5, 0))
            self.search_var.trace_add("write", lambda *_args: self.refresh())
            self.supplier_var.trace_add("write", lambda *_args: self.refresh())
            self.sort_var.trace_add("write", lambda *_args: self.refresh())

        self.result_label = tk.Label(self, bg=WHITE, font=(FONT, 10, "bold"))
        self.result_label.pack(anchor="w", padx=20, pady=(0, 5))
        container = tk.Frame(self, bg=WHITE)
        container.pack(fill="both", expand=True, padx=18, pady=(0, 14))
        self.canvas = tk.Canvas(container, bg=WHITE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            container, orient="vertical", command=self.canvas.yview
        )
        self.cards_frame = tk.Frame(self.canvas, bg=WHITE)
        self.window_id = self.canvas.create_window(
            (0, 0), window=self.cards_frame, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.cards_frame.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda event: self.canvas.itemconfigure(self.window_id, width=event.width),
        )
        self.canvas.bind_all(
            "<MouseWheel>",
            lambda event: self.canvas.yview_scroll(int(-event.delta / 120), "units"),
        )
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.refresh()

    def refresh(self):
        for child in self.cards_frame.winfo_children():
            child.destroy()
        try:
            products = db.get_products(
                self.search_var.get(), self.supplier_var.get(), self.sort_var.get()
            )
        except sqlite3.Error as error:
            messagebox.showerror(
                "Ошибка загрузки",
                f"Не удалось получить список товаров.\n\n{error}",
                parent=self,
            )
            return
        self.result_label.configure(text=f"Найдено товаров: {len(products)}")
        if not products:
            tk.Label(
                self.cards_frame,
                text="По заданным условиям товары не найдены.",
                bg=WHITE,
                font=(FONT, 12),
                pady=30,
            ).pack()
            return
        for product in products:
            self.create_product_card(product)

    def bind_card(self, widget, product_id):
        widget.bind(
            "<Button-1>",
            lambda _event: self.master.open_product_editor(product_id)
            if self.role == "Администратор"
            else None,
        )
        for child in widget.winfo_children():
            self.bind_card(child, product_id)

    def create_product_card(self, product):
        background = WHITE
        if product["stock"] == 0:
            background = OUT_OF_STOCK_BACKGROUND
        elif product["discount"] > 17:
            background = DISCOUNT_BACKGROUND
        card = tk.Frame(
            self.cards_frame,
            bg=background,
            bd=1,
            relief="solid",
            padx=12,
            pady=10,
            cursor="hand2" if self.role == "Администратор" else "",
        )
        card.pack(fill="x", pady=4)
        photo = load_photo(product["image_path"], (130, 95))
        image_label = tk.Label(card, image=photo, bg=background)
        image_label.image = photo
        image_label.pack(side="left", padx=(0, 14))

        details = tk.Frame(card, bg=background)
        details.pack(side="left", fill="both", expand=True)
        tk.Label(
            details,
            text=f"{product['article']} | {product['name']}",
            bg=background,
            anchor="w",
            justify="left",
            wraplength=760,
            font=(FONT, 11, "bold"),
        ).pack(fill="x")
        tk.Label(
            details,
            text=(
                f"Категория: {product['category']}   |   Производитель: "
                f"{product['manufacturer']}   |   Поставщик: {product['supplier']}"
            ),
            bg=background,
            anchor="w",
            justify="left",
            wraplength=820,
        ).pack(fill="x", pady=(4, 0))
        tk.Label(
            details,
            text=product["description"],
            bg=background,
            anchor="w",
            justify="left",
            wraplength=820,
        ).pack(fill="x", pady=(4, 0))

        price_panel = tk.Frame(card, bg=background, width=175)
        price_panel.pack(side="right", fill="y", padx=(12, 0))
        final_price = product["price"] * (1 - product["discount"] / 100)
        if product["discount"] > 0:
            tk.Label(
                price_panel,
                text=f"{product['price']:.2f} руб.",
                fg="red",
                bg=background,
                font=(FONT, 10, "overstrike"),
            ).pack(anchor="e")
            tk.Label(
                price_panel,
                text=f"{final_price:.2f} руб.",
                bg=background,
                font=(FONT, 12, "bold"),
            ).pack(anchor="e")
        else:
            tk.Label(
                price_panel,
                text=f"{product['price']:.2f} руб.",
                bg=background,
                font=(FONT, 12, "bold"),
            ).pack(anchor="e")
        tk.Label(
            price_panel,
            text=f"Скидка: {product['discount']}%",
            bg=background,
        ).pack(anchor="e", pady=(6, 0))
        tk.Label(
            price_panel,
            text=f"На складе: {product['stock']} {product['unit']}",
            bg=background,
            font=(FONT, 10, "bold"),
        ).pack(anchor="e", pady=(4, 0))
        self.bind_card(card, product["id"])


class ProductEditor(tk.Toplevel):
    def __init__(self, master, product_id=None):
        super().__init__(master)
        self.master_app = master
        self.product_id = product_id
        self.product = db.get_product(product_id) if product_id else None
        self.selected_image = None
        self.title("Редактирование товара" if product_id else "Добавление товара")
        self.configure(bg=WHITE)
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.close)
        center_window(self, 720, 760)
        self.create_form()

    def create_form(self):
        heading = tk.Label(
            self,
            text=self.title(),
            bg=SECONDARY,
            font=(FONT, 16, "bold"),
            pady=12,
        )
        heading.pack(fill="x")
        form = tk.Frame(self, bg=WHITE, padx=22, pady=14)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        self.variables = {
            "article": tk.StringVar(),
            "name": tk.StringVar(),
            "category": tk.StringVar(),
            "manufacturer": tk.StringVar(),
            "supplier": tk.StringVar(),
            "price": tk.StringVar(),
            "unit": tk.StringVar(value="шт."),
            "stock": tk.StringVar(value="0"),
            "discount": tk.StringVar(value="0"),
        }
        row = 0
        if self.product:
            tk.Label(form, text="ID товара", bg=WHITE, anchor="w").grid(
                row=row, column=0, sticky="w", pady=4
            )
            ttk.Entry(form, state="readonly", width=40).grid(
                row=row, column=1, sticky="ew", pady=4
            )
            id_entry = form.grid_slaves(row=row, column=1)[0]
            id_entry.configure(state="normal")
            id_entry.insert(0, str(self.product["id"]))
            id_entry.configure(state="readonly")
            row += 1
        for key, label in (
            ("article", "Артикул"),
            ("name", "Наименование"),
            ("category", "Категория"),
            ("manufacturer", "Производитель"),
            ("supplier", "Поставщик"),
            ("price", "Цена"),
            ("unit", "Единица измерения"),
            ("stock", "Количество на складе"),
            ("discount", "Действующая скидка, %"),
        ):
            tk.Label(form, text=label, bg=WHITE, anchor="w").grid(
                row=row, column=0, sticky="w", pady=4, padx=(0, 12)
            )
            if key in ("category", "supplier"):
                table = "categories" if key == "category" else "suppliers"
                widget = ttk.Combobox(
                    form,
                    textvariable=self.variables[key],
                    values=[item["value"] for item in db.get_lookup(table)],
                    state="readonly",
                )
            else:
                widget = ttk.Entry(form, textvariable=self.variables[key])
            widget.grid(row=row, column=1, sticky="ew", pady=4)
            row += 1
        tk.Label(form, text="Описание", bg=WHITE, anchor="nw").grid(
            row=row, column=0, sticky="nw", pady=4
        )
        self.description_text = tk.Text(
            form, height=6, wrap="word", font=(FONT, 10), relief="solid", bd=1
        )
        self.description_text.grid(row=row, column=1, sticky="nsew", pady=4)
        row += 1
        tk.Label(form, text="Фото", bg=WHITE, anchor="nw").grid(
            row=row, column=0, sticky="nw", pady=4
        )
        image_panel = tk.Frame(form, bg=WHITE)
        image_panel.grid(row=row, column=1, sticky="w", pady=4)
        current_path = (
            self.product["image_path"]
            if self.product
            else os.path.join("assets", "images", "picture.png")
        )
        photo = load_photo(current_path, (180, 120))
        self.image_label = tk.Label(image_panel, image=photo, bg=WHITE)
        self.image_label.image = photo
        self.image_label.pack(side="left")
        ttk.Button(
            image_panel, text="Выбрать изображение", command=self.choose_image
        ).pack(side="left", padx=12)
        row += 1
        buttons = tk.Frame(form, bg=WHITE)
        buttons.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        ttk.Button(buttons, text="Сохранить", command=self.save).pack(side="left")
        ttk.Button(buttons, text="Отмена", command=self.close).pack(
            side="left", padx=8
        )
        if self.product:
            ttk.Button(buttons, text="Удалить товар", command=self.delete).pack(
                side="right"
            )
        if self.product:
            for key in self.variables:
                self.variables[key].set(str(self.product[key]))
            self.description_text.insert("1.0", self.product["description"])

    def choose_image(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Выберите изображение товара",
            filetypes=[
                ("Изображения", "*.png *.jpg *.jpeg *.bmp"),
                ("Все файлы", "*.*"),
            ],
        )
        if not path:
            return
        try:
            with Image.open(path) as image:
                image.verify()
            self.selected_image = path
            photo = load_photo(path, (180, 120))
            self.image_label.configure(image=photo)
            self.image_label.image = photo
        except Exception as error:
            messagebox.showerror(
                "Некорректное изображение",
                f"Выбранный файл не удалось прочитать как изображение.\n\n{error}",
                parent=self,
            )

    def validate(self):
        values = {key: variable.get().strip() for key, variable in self.variables.items()}
        values["description"] = self.description_text.get("1.0", "end").strip()
        required = {
            "article": "артикул",
            "name": "наименование",
            "category": "категорию",
            "manufacturer": "производителя",
            "supplier": "поставщика",
            "unit": "единицу измерения",
            "description": "описание",
        }
        missing = [label for key, label in required.items() if not values[key]]
        if missing:
            raise ValueError("Заполните обязательные поля: " + ", ".join(missing))
        try:
            values["price"] = float(values["price"].replace(",", "."))
            values["stock"] = int(values["stock"])
            values["discount"] = int(values["discount"])
        except ValueError as error:
            raise ValueError(
                "Цена должна быть числом, количество и скидка — целыми числами."
            ) from error
        if values["price"] < 0:
            raise ValueError("Цена не может быть отрицательной.")
        if values["stock"] < 0:
            raise ValueError("Количество на складе не может быть отрицательным.")
        if not 0 <= values["discount"] <= 100:
            raise ValueError("Скидка должна находиться в диапазоне от 0 до 100%.")
        return values

    def prepare_image(self):
        if not self.selected_image:
            return (
                self.product["image_path"]
                if self.product
                else os.path.join("assets", "images", "picture.png")
            )
        images_dir = asset_path("images")
        os.makedirs(images_dir, exist_ok=True)
        file_name = f"product_{uuid.uuid4().hex}.jpg"
        destination = os.path.join(images_dir, file_name)
        with Image.open(self.selected_image) as image:
            image = image.convert("RGB")
            image.thumbnail((300, 200), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (300, 200), WHITE)
            offset = ((300 - image.width) // 2, (200 - image.height) // 2)
            canvas.paste(image, offset)
            canvas.save(destination, "JPEG", quality=90)
        return os.path.join("assets", "images", file_name)

    def save(self):
        try:
            values = self.validate()
            new_image_path = self.prepare_image()
            old_image_path = self.product["image_path"] if self.product else None
            values["image_path"] = new_image_path
            db.save_product(values, self.product_id)
            if (
                self.selected_image
                and old_image_path
                and not old_image_path.endswith("picture.png")
                and old_image_path != new_image_path
            ):
                old_full_path = os.path.join(db.APP_DIR, old_image_path)
                if os.path.exists(old_full_path):
                    os.remove(old_full_path)
            messagebox.showinfo(
                "Данные сохранены",
                "Товар успешно сохранен в базе данных.",
                parent=self,
            )
            self.close(refresh=True)
        except (ValueError, sqlite3.IntegrityError) as error:
            messagebox.showerror(
                "Ошибка сохранения",
                f"Проверьте введенные данные.\n\n{error}",
                parent=self,
            )
        except Exception as error:
            messagebox.showerror(
                "Ошибка сохранения",
                f"Не удалось сохранить товар.\n\n{error}",
                parent=self,
            )

    def delete(self):
        if not messagebox.askyesno(
            "Подтверждение удаления",
            "Удалить выбранный товар? Операцию нельзя отменить.",
            icon="warning",
            parent=self,
        ):
            return
        try:
            db.delete_product(self.product_id)
            messagebox.showinfo(
                "Товар удален", "Товар успешно удален.", parent=self
            )
            self.close(refresh=True)
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Удаление запрещено",
                "Товар присутствует в одном или нескольких заказах и не может "
                "быть удален. Сначала удалите товар из заказов.",
                parent=self,
            )
        except sqlite3.Error as error:
            messagebox.showerror(
                "Ошибка удаления",
                f"Не удалось удалить товар.\n\n{error}",
                parent=self,
            )

    def close(self, refresh=False):
        self.grab_release()
        self.master_app.product_editor = None
        self.destroy()
        if refresh and isinstance(self.master_app.current_frame, ProductListFrame):
            self.master_app.current_frame.refresh()


class OrderListFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=WHITE)
        self.role = master.current_user["role"]
        Header(self, "Заказы", show_back=True).pack(fill="x")
        actions = tk.Frame(self, bg=WHITE, padx=18, pady=10)
        actions.pack(fill="x")
        if self.role == "Администратор":
            ttk.Button(
                actions,
                text="Добавить заказ",
                command=lambda: master.open_order_editor(),
            ).pack(side="left")
        tk.Label(
            actions,
            text="Двойной щелчок открывает заказ"
            if self.role == "Администратор"
            else "Режим просмотра",
            bg=WHITE,
        ).pack(side="right")
        columns = (
            "id",
            "items",
            "order_date",
            "delivery_date",
            "address",
            "client",
            "code",
            "status",
        )
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        headings = {
            "id": "№",
            "items": "Состав заказа",
            "order_date": "Дата заказа",
            "delivery_date": "Дата выдачи",
            "address": "Пункт выдачи",
            "client": "Клиент",
            "code": "Код",
            "status": "Статус",
        }
        widths = {
            "id": 45,
            "items": 210,
            "order_date": 95,
            "delivery_date": 95,
            "address": 250,
            "client": 190,
            "code": 65,
            "status": 90,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], minwidth=45)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(18, 0), pady=(0, 18))
        scrollbar.pack(side="right", fill="y", padx=(0, 18), pady=(0, 18))
        if self.role == "Администратор":
            self.tree.bind("<Double-1>", self.edit_selected)
        self.refresh()

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            for order in db.get_orders():
                self.tree.insert(
                    "",
                    "end",
                    iid=str(order["id"]),
                    values=(
                        order["id"],
                        order["items"] or "",
                        order["order_date"],
                        order["delivery_date"],
                        order["address"],
                        order["client"],
                        order["receive_code"] or "",
                        order["status"],
                    ),
                )
        except sqlite3.Error as error:
            messagebox.showerror(
                "Ошибка загрузки",
                f"Не удалось получить список заказов.\n\n{error}",
                parent=self,
            )

    def edit_selected(self, _event=None):
        selected = self.tree.selection()
        if selected:
            self.master.open_order_editor(int(selected[0]))


class OrderEditor(tk.Toplevel):
    def __init__(self, master, order_id=None):
        super().__init__(master)
        self.master_app = master
        self.order_id = order_id
        self.order, self.items = db.get_order(order_id) if order_id else (None, [])
        self.title("Редактирование заказа" if order_id else "Добавление заказа")
        self.configure(bg=WHITE)
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.close)
        center_window(self, 760, 610)
        self.create_form()

    def create_form(self):
        tk.Label(
            self,
            text=self.title(),
            bg=SECONDARY,
            font=(FONT, 16, "bold"),
            pady=12,
        ).pack(fill="x")
        form = tk.Frame(self, bg=WHITE, padx=24, pady=18)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        self.item_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Новый")
        self.address_var = tk.StringVar()
        self.order_date_var = tk.StringVar(value=datetime.now().strftime("%d.%m.%Y"))
        self.delivery_date_var = tk.StringVar(value=datetime.now().strftime("%d.%m.%Y"))
        self.client_var = tk.StringVar()
        self.code_var = tk.StringVar()
        fields = [
            (
                "Состав (АРТИКУЛ, количество; ...)",
                ttk.Entry(form, textvariable=self.item_var),
            ),
            (
                "Статус заказа",
                ttk.Combobox(
                    form,
                    textvariable=self.status_var,
                    values=["Новый", "В обработке", "Готов к выдаче", "Завершен"],
                    state="readonly",
                ),
            ),
            (
                "Адрес пункта выдачи",
                ttk.Combobox(
                    form,
                    textvariable=self.address_var,
                    values=[
                        item["value"] for item in db.get_lookup("pickup_points")
                    ],
                    state="readonly",
                ),
            ),
            ("Дата заказа (ДД.ММ.ГГГГ)", ttk.Entry(form, textvariable=self.order_date_var)),
            (
                "Дата выдачи (ДД.ММ.ГГГГ)",
                ttk.Entry(form, textvariable=self.delivery_date_var),
            ),
        ]
        clients = db.get_clients()
        self.client_map = {item["full_name"]: item["id"] for item in clients}
        fields.extend(
            [
                (
                    "Клиент",
                    ttk.Combobox(
                        form,
                        textvariable=self.client_var,
                        values=list(self.client_map.keys()),
                        state="readonly",
                    ),
                ),
                ("Код получения", ttk.Entry(form, textvariable=self.code_var)),
            ]
        )
        for row, (label, widget) in enumerate(fields):
            tk.Label(form, text=label, bg=WHITE, anchor="w").grid(
                row=row, column=0, sticky="w", pady=7, padx=(0, 12)
            )
            widget.grid(row=row, column=1, sticky="ew", pady=7)
        tk.Label(
            form,
            text="Пример: PMEZMH, 2; BPV4MM, 1",
            bg=WHITE,
            fg="#555555",
        ).grid(row=len(fields), column=1, sticky="w")
        buttons = tk.Frame(form, bg=WHITE)
        buttons.grid(
            row=len(fields) + 1, column=0, columnspan=2, sticky="ew", pady=(22, 0)
        )
        ttk.Button(buttons, text="Сохранить", command=self.save).pack(side="left")
        ttk.Button(buttons, text="Отмена", command=self.close).pack(
            side="left", padx=8
        )
        if self.order:
            ttk.Button(buttons, text="Удалить заказ", command=self.delete).pack(
                side="right"
            )
            self.item_var.set(
                "; ".join(
                    f"{item['article']}, {item['quantity']}" for item in self.items
                )
            )
            self.status_var.set(self.order["status"])
            self.address_var.set(self.order["address"])
            self.order_date_var.set(self.order["order_date"])
            self.delivery_date_var.set(self.order["delivery_date"])
            self.client_var.set(self.order["client"])
            self.code_var.set(str(self.order["receive_code"] or ""))

    def validate(self):
        raw_items = self.item_var.get().strip()
        if not raw_items:
            raise ValueError("Укажите хотя бы один товар в составе заказа.")
        items = []
        seen_articles = set()
        for raw_item in raw_items.split(";"):
            parts = [part.strip() for part in raw_item.split(",")]
            if len(parts) != 2 or not parts[0]:
                raise ValueError(
                    "Состав заказа должен иметь формат: АРТИКУЛ, количество; ..."
                )
            article = parts[0]
            try:
                quantity = int(parts[1])
            except ValueError as error:
                raise ValueError(
                    f"Количество для товара {article} должно быть целым числом."
                ) from error
            if quantity <= 0:
                raise ValueError(f"Количество для товара {article} должно быть больше 0.")
            if article in seen_articles:
                raise ValueError(f"Артикул {article} указан в заказе несколько раз.")
            seen_articles.add(article)
            items.append((article, quantity))
        try:
            order_date = datetime.strptime(
                self.order_date_var.get().strip(), "%d.%m.%Y"
            )
            delivery_date = datetime.strptime(
                self.delivery_date_var.get().strip(), "%d.%m.%Y"
            )
        except ValueError as error:
            raise ValueError("Введите даты в формате ДД.ММ.ГГГГ.") from error
        if delivery_date < order_date:
            raise ValueError("Дата выдачи не может быть раньше даты заказа.")
        if not self.status_var.get() or not self.address_var.get():
            raise ValueError("Выберите статус и пункт выдачи.")
        code_text = self.code_var.get().strip()
        if code_text:
            try:
                receive_code = int(code_text)
            except ValueError as error:
                raise ValueError("Код получения должен быть целым числом.") from error
        else:
            receive_code = None
        return (
            {
                "order_date": order_date.strftime("%d.%m.%Y"),
                "delivery_date": delivery_date.strftime("%d.%m.%Y"),
                "status": self.status_var.get(),
                "address": self.address_var.get(),
                "client_id": self.client_map.get(self.client_var.get()),
                "receive_code": receive_code,
            },
            items,
        )

    def save(self):
        try:
            values, items = self.validate()
            db.save_order(values, items, self.order_id)
            messagebox.showinfo(
                "Данные сохранены", "Заказ успешно сохранен.", parent=self
            )
            self.close(refresh=True)
        except (ValueError, sqlite3.IntegrityError) as error:
            messagebox.showerror(
                "Ошибка сохранения",
                f"Проверьте введенные данные.\n\n{error}",
                parent=self,
            )
        except sqlite3.Error as error:
            messagebox.showerror(
                "Ошибка базы данных",
                f"Не удалось сохранить заказ.\n\n{error}",
                parent=self,
            )

    def delete(self):
        if not messagebox.askyesno(
            "Подтверждение удаления",
            "Удалить выбранный заказ? Операцию нельзя отменить.",
            icon="warning",
            parent=self,
        ):
            return
        try:
            db.delete_order(self.order_id)
            messagebox.showinfo(
                "Заказ удален", "Заказ успешно удален.", parent=self
            )
            self.close(refresh=True)
        except sqlite3.Error as error:
            messagebox.showerror(
                "Ошибка удаления",
                f"Не удалось удалить заказ.\n\n{error}",
                parent=self,
            )

    def close(self, refresh=False):
        self.grab_release()
        self.master_app.order_editor = None
        self.destroy()
        if refresh and isinstance(self.master_app.current_frame, OrderListFrame):
            self.master_app.current_frame.refresh()


def main():
    if not os.path.exists(db.DATABASE_PATH):
        messagebox.showerror(
            "База данных не найдена",
            f"Файл базы данных отсутствует:\n{db.DATABASE_PATH}",
        )
        return
    application = ToyStoreApplication()
    application.mainloop()


if __name__ == "__main__":
    main()
