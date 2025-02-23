import os
import requests
# import imghdr
import configparser
import tkinter as tk
from tkinter import filedialog, messagebox
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from PIL import Image
from io import BytesIO
import random

# =============== CONFIGURATION FILE SETUP ===============
CONFIG_FILE = "config_WeSyncPress.ini"

def create_default_config():
    """Creates a default config file if none exists"""
    config = configparser.ConfigParser()
    media_stamp = random.randint(1000, 9999)
    config["SETTINGS"] = {
        "URL": "https://example.com/article",
        "OUTPUT_FOLDER": "article_output",
        "DRAFT_HTML_FILE": "draft_html.html",
        "CLEAN_HTML_FILE": "clean_html.html",
        "MEDIA_STAMP": f"{media_stamp}",
        "MEDIA_SRC": "https://uploads.example.com/or-a-local-path/",
    }
    with open(CONFIG_FILE, "w") as configfile:
        config.write(configfile)

def load_config():
    """Loads the config file or creates a default one"""
    if not os.path.exists(CONFIG_FILE):
        create_default_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config

# =============== GUI CONFIGURATION EDITOR ===============
def contact_developer():
    """Opens a simple Contact Developer window"""
    contact_window = tk.Toplevel()
    contact_window.title("Contact Developer - 联系开发者")

    contact_info = """
    📌 WeSyncPress Support
    ──────────────────────────────────────────────────────────────────────────
    🔹 Developer - 开发者: Yu-Yawei
    📦 GitHub & Manual - 代码与使用说明: https://github.com/Yu-Yawei/WeSyncPress
    ──────────────────────────────────────────────────────────────────────────
    If you experience any issues or would like to request new features, please contact me via GitHub.
    如有任何问题或需求新功能，请通过GitHub联系我。
    """

    tk.Label(contact_window, text=contact_info, justify="left", font=("Arial", 10)).pack(padx=20, pady=20)
    tk.Button(contact_window, text="Close", command=contact_window.destroy).pack(pady=10)

def edit_config_gui():
    """Launches a Tkinter GUI for editing the configuration"""
    config = load_config()

    fields = {
        # "URL": "URL of the article to be extracted",
        # "OUTPUT_FOLDER": "Output folder for images and HTML",
        # "MEDIA_STAMP": "Media stamp for image filenames",
        # "MEDIA_SRC": "Base URL or path for images",
        # "DRAFT_HTML_FILE": "Draft HTML file name",
        # "CLEAN_HTML_FILE": "Clean HTML file name",
        "URL": "待导出文章所在网页",
        "OUTPUT_FOLDER": "导出图片与文章HTML输出文件夹",
        "MEDIA_STAMP": "为同一篇文章导出的所有图片设置名称标记",
        "MEDIA_SRC": "设置该路径为WordPress图片库网页链接或本地文件夹路径，文章及图片导出后请将图片上传至该路径",
        "DRAFT_HTML_FILE": "草稿HTML文件名",
        "CLEAN_HTML_FILE": "定稿HTML文件名",
    }
    
    def save_and_exit():
        """Saves the user-edited values and exits the GUI"""
        for key, entry in entries.items():
            config["SETTINGS"][key] = entry.get()
        with open(CONFIG_FILE, "w") as configfile:
            config.write(configfile)
        # messagebox.showinfo("Saved", "Configuration saved successfully!")
        messagebox.showinfo("Saved", "设置已成功保存！")
        root.destroy()

    root = tk.Tk()
    root.title("Set Up before Sync - 同步前设置")

    entries = {}

    for i, (key, label) in enumerate(fields.items()):
        tk.Label(root, text=label + ":", wraplength = 300, justify='left').grid(row=2*i, column=0, sticky="w", padx=5, pady=2)
        entry = tk.Entry(root, width=50)
        entry.grid(row=2*i+1, column=0, padx=5, pady=2)
        entry.insert(0, config["SETTINGS"].get(key, ""))  # Load existing config value
        entries[key] = entry  # Store reference in dictionary

    tk.Button(root, text="保存并退出", command=save_and_exit).grid(row=2*(i+1), columnspan=2)

    root.mainloop()

# =============== MAIN EXTRACTION FUNCTION ===============
def extract_article():
    """Extracts the article content, images, and CSS"""
    config = load_config()
    URL = config["SETTINGS"]["URL"]
    OUTPUT_FOLDER = config["SETTINGS"]["OUTPUT_FOLDER"]
    DRAFT_HTML_FILE = config["SETTINGS"]["DRAFT_HTML_FILE"]
    MEDIA_SRC = config["SETTINGS"]["MEDIA_SRC"]
    MEDIA_STAMP = config["SETTINGS"]["MEDIA_STAMP"]

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
    if response.status_code != 200:
        # messagebox.showerror("Error", f"Failed to fetch page: {response.status_code}")
        messagebox.showerror("Error", f"无法获取网页内容: {response.status_code}")
        return
    
    soup = BeautifulSoup(response.content, "html.parser")
    article_div = soup.find("div", id="page-content")
    if not article_div:
        # messagebox.showerror("Error", "Article content not found!")
        messagebox.showerror("Error", "未找到文章内容！")
        return

    # Extract CSS styles
    css_styles = ""
    css_styles += """
    * { visibility: visible !important; opacity: 1 !important; }
    body, div, p, h1, h2, h3, span, img, a, table, tr, td, ul, li {
        visibility: inherit !important;
        opacity: inherit !important;
    }
    """

    for style_tag in soup.find_all("style"):
        css_styles += style_tag.prettify()

    # Extract external CSS files and download them
    external_css_links = [link["href"] for link in soup.find_all("link", rel="stylesheet") if "href" in link.attrs]

    for css_link in external_css_links:
        full_css_url = urljoin(URL, css_link)
        css_response = requests.get(full_css_url, headers={"User-Agent": "Mozilla/5.0"})
        if css_response.status_code == 200:
            css_filename = os.path.join(OUTPUT_FOLDER, os.path.basename(css_link))
            with open(css_filename, "w", encoding="utf-8") as css_file:
                css_file.write(css_response.text)
            css_styles += f'\n<link rel="stylesheet" href="{MEDIA_SRC}{os.path.basename(css_link)}">\n'
        else:
            # messagebox.showerror(f"Failed to download CSS: {full_css_url}")
            messagebox.showerror("Error", f"无法下载CSS文件: {full_css_url}")

    # Extract all images and update paths
    image_count = 0
    for img_tag in article_div.find_all("img"):
        img_url = img_tag.get("src") or img_tag.get("data-src")  # Handle lazy loading
        if img_url:
            full_img_url = urljoin(URL, img_url)
            img_response = requests.get(full_img_url, headers={"User-Agent": "Mozilla/5.0"})
            if img_response.status_code == 200:
                image_data = BytesIO(img_response.content)
                # detected_format = imghdr.what(image_data)  # Detect format (jpg, png, etc.)
                detected_format = None

                # If imghdr fails, use PIL as a fallback
                if not detected_format:
                    try:
                        with Image.open(image_data) as img:
                            detected_format = img.format.lower()
                    except Exception as e:
                        # messagebox.showerror(f"Warning: Could not detect format for {full_img_url}. Defaulting to jpg.")
                        messagebox.showerror("Warning", f"警告: 无法检测图片格式 {full_img_url}，默认使用jpg格式。")
                        detected_format = "jpg"

                img_filename = f"image_{MEDIA_STAMP}_{image_count + 1}.{detected_format}"
                img_path = os.path.join(OUTPUT_FOLDER, img_filename)
                with open(img_path, "wb") as img_file:
                    img_file.write(img_response.content)
                # Update image path in HTML
                img_tag["src"] = MEDIA_SRC + img_filename
                image_count += 1
            else:
                # messagebox.showerror(f"Failed to download image: {full_img_url}")
                messagebox.showerror("Error", f"无法下载图片: {full_img_url}")

    for p_tag in article_div.find_all("p"):
        if "http" in p_tag.get_text():
            # Prevent WordPress link preview by inserting an invisible zero-width space
            p_tag.string = p_tag.get_text().replace("https://", "https:\u200B//")

    # Save extracted content as WordPress-compatible HTML
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    {css_styles}
    </style>
    </head>
    <body>
    {article_div.prettify()}  <!-- Preserve full HTML structure -->
    </body>
    </html>
    """

    # Save full_html before user edits
    full_html_path = os.path.join(OUTPUT_FOLDER, DRAFT_HTML_FILE)
    with open(full_html_path, "w", encoding="utf-8") as file:
        file.write(full_html)

    # messagebox.showinfo(f"\n✅ Extraction Complete! Edit `{full_html_path}` before proceeding.")
    messagebox.showinfo("提示信息", f"\n提取完成。{image_count} 张图片已下载至文件夹: {OUTPUT_FOLDER}\n请将图片上传至您的网站媒体库，并在编辑文件 `{full_html_path}` 后使用调整格式功能。")
    # messagebox.showinfo(f"✅ {image_count} images downloaded to folder: {OUTPUT_FOLDER}\nUpload them to your website media library.")
    # messagebox.showinfo(f"✅ {image_count} 张图片已下载至文件夹: {OUTPUT_FOLDER}\n请将图片上传至您的网站媒体库。")

# =============== CLEAN UP HTML FUNCTION ===============
def clean_html():
    """Reads the manually edited HTML and converts it to a single-line format"""
    config = load_config()
    OUTPUT_FOLDER = config["SETTINGS"]["OUTPUT_FOLDER"]
    DRAFT_HTML_FILE = config["SETTINGS"]["DRAFT_HTML_FILE"]
    CLEAN_HTML_FILE = config["SETTINGS"]["CLEAN_HTML_FILE"]

    full_html_path = os.path.join(OUTPUT_FOLDER, DRAFT_HTML_FILE)
    clean_html_path = os.path.join(OUTPUT_FOLDER, CLEAN_HTML_FILE)

    if not os.path.exists(full_html_path):
        # messagebox.showerror("Error: Draft HTML file not found! Please export one and edit it first.")
        messagebox.showerror("Error", "错误: 未找到草稿HTML文件！请先导出并编辑草稿HTML文件。")
        return

    with open(full_html_path, "r", encoding="utf-8") as file:
        full_html = file.read()

    clean_html = "".join(full_html.splitlines())

    with open(clean_html_path, "w", encoding="utf-8") as file:
        file.write(clean_html)

    # messagebox.showinfo(f"\n✅ Formatted HTML saved to: `{clean_html_path}`\nYou can now paste this into your WordPress editor.")
    messagebox.showinfo("提示信息", f"\n已保存调整格式后的HTML至: `{clean_html_path}`\n您可以将其内容复制粘贴至WordPress编辑器了。")

# =============== MAIN MENU FOR USER INTERACTION ===============
def main_gui():
    """Creates the main GUI menu"""
    root = tk.Tk()
    root.title("WeSyncPress - WeChat to WordPress Sync")

    tk.Label(root, text="WeSyncPress", font=("Arial", 14, "bold")).pack(pady=10)

    tk.Button(root, text="Set Up before Sync - 同步前设置", width=50, bg="steelblue", fg='white', command=edit_config_gui).pack(pady=5)
    tk.Button(root, text="Extract Article Draft - 导出文章草稿", width=50, bg="steelblue", fg='white', command=extract_article).pack(pady=5)
    tk.Button(root, text="Format Draft for WordPress - 调整为WordPress适用格式", width=50, bg="steelblue", fg='white', command=clean_html).pack(pady=5)
    tk.Button(root, text="Contact Developer - 联系开发者", width=30, command=contact_developer).pack(pady=5)
    tk.Button(root, text="Exit - 退出", width=30, command=root.quit).pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main_gui()
