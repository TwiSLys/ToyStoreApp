import os
import time

from PIL import ImageGrab

import db
from app import ToyStoreApplication


ROOT = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(ROOT, "docs", "screenshots")


def capture(application, file_name):
    application.update_idletasks()
    application.update()
    application.lift()
    application.attributes("-topmost", True)
    application.update()
    application.attributes("-topmost", False)
    time.sleep(0.8)
    x = application.winfo_rootx()
    y = application.winfo_rooty()
    width = application.winfo_width()
    height = application.winfo_height()
    image = ImageGrab.grab((x, y, x + width, y + height))
    image.save(os.path.join(SCREENSHOT_DIR, file_name))


def main():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    application = ToyStoreApplication()
    capture(application, "01_login.png")
    admin = db.authenticate("94d5ous@gmail.com", "uzWC67")
    application.show_products(admin)
    capture(application, "02_products_admin.png")
    application.show_orders()
    capture(application, "03_orders_admin.png")
    application.destroy()
    print(f"Screenshots saved to {SCREENSHOT_DIR}")


if __name__ == "__main__":
    main()
