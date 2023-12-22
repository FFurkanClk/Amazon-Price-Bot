import pandas as pd
import requests
from bs4 import BeautifulSoup
import pymongo
import time
import tkinter as tk
from tkinter import Listbox, Scrollbar, END, ttk, messagebox  

root = tk.Tk()
root.title("Amazon Ürün Takip Botu")

# MongoDB bağlantısı
myclient = pymongo.MongoClient("mongodb+srv://furkan:*****@cluster0.9tksluj.mongodb.net/")
mydb = myclient["amazondb"]
mycol = mydb["productsamazon"]

# Kullanıcı  başlığı
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.36"
}

# URLden veri almak için işlev
def get_data(url1):
    r = requests.get(url1, headers=headers)
    soup = BeautifulSoup(r.content, "html.parser")
    return soup

# URLleri bir dosyadan okumak için işlev
def read_urls():
    with open(r'C:\Users\furka\Desktop\urls.txt') as f:
        urls = f.readlines()
    return urls

# Ürün verilerini  yazmak ve güncellemek için işlev
def parse_and_update(urllist):
    existing_titles = set()
    for existing_product in mycol.find():
        existing_titles.add(existing_product["title"])

    new_product_list = []
    for ul in urllist:
        parts = ul.split("price:")

        if len(parts) == 2:
            url = parts[0].strip()
            check_price = float(parts[1].strip())

            soup = get_data(url)
            title = soup.find("span", attrs={"class": "a-size-large product-title-word-break"}).text.strip()

            if title not in existing_titles:
                if soup.find("span", attrs={"class": "a-offscreen"}) is not None:
                    price = float((soup.find("span", attrs={"class": "a-offscreen"}).text.strip().replace("TL", "")).replace(",00", ""))
                else:
                    price = None

                print("Başlık:", title, "\n", "Fiyat:", price, "\n", "Kontrol Fiyatı:", check_price)

                if price is not None:
                    if check_price > price:
                        print("  İNDİRİM VAR  ")

                # Yeni ürün bilgilerini listeye ekle
                info = {"title": title, "price": price, "check_price": check_price}
                new_product_list.append(info)
                if existing_product:
                    print(f"{title} adlı ürün zaten veritabanında mevcut.")
                    # Kullanıcıya uyarı mesajı göster
                    messagebox.showinfo("Uyarı", f"{title} adlı ürün zaten veritabanında mevcut.")
                else:
                    mycol.insert_one(info)
                    print(f"{title} adlı ürün veritabanına eklendi.")

            else:
                print(f"urls.txt dosyasındaki satır atlanıyor: {ul.strip()}")

    return new_product_list

# GUIda ürün listesini güncellemek için işlev
def update_listbox():
    urllist = read_urls()
    new_product_list = parse_and_update(urllist)

    listbox.delete(0, END)

    for product in new_product_list:
        listbox.insert(END, f"Başlık: {product['title']}, Fiyat: {product['price']}")

# GUIda tüm ürünleri göstermek için işlev
def show_all_products():
    all_products = mycol.find()

    listbox.delete(0, END)

    for product in all_products:
        listbox.insert(END, f"Başlık: {product['title']}, Fiyat: {product['price']}")

# Yeni bir ürün URL'si eklemek için işlev
def add_product_window():
    add_window = tk.Toplevel(root)
    add_window.title("Ürün Ekle")

    entry_label = tk.Label(add_window, text="Ürün Linki:")
    entry_label.pack(padx=10, pady=5)
    entry = tk.Entry(add_window, width=60)
    entry.pack(padx=10, pady=5)

    def add_product():
        product_url = entry.get()
        if product_url:
            with open(r'C:\Users\furka\Desktop\urls.txt', 'a') as f:
                f.write(f"{product_url}\n")
            entry.delete(0, tk.END)
            add_window.destroy()

            # Eklenen ürünü veritabanında kontrol et
            soup = get_data(product_url)
            title = soup.find("span", attrs={"class": "a-size-large product-title-word-break"}).text.strip()
            existing_product = mycol.find_one({"title": title})

            if existing_product:
                print(f"{title} adlı ürün zaten veritabanında mevcut.")
                # Kullanıcıya uyarı mesajı göster
                messagebox.showinfo("Uyarı", f"{title} adlı ürün zaten veritabanında mevcut.")
            else:
                info = {"title": title, "price": None, "check_price": None}
                mycol.insert_one(info)
                print(f"{title} adlı ürün veritabanına eklendi.")
                messagebox.showinfo("Uyarı", f"{title} adlı ürün veritabanına eklendi.")

    add_button = tk.Button(add_window, text="Ekle", command=add_product)
    add_button.pack(pady=5)

# Tabloda ürün verilerini görüntülemek için işlev
def display_data():
    # Tablodaki mevcut verileri temizle
    for row in tree.get_children():
        tree.delete(row)

    # Veritabanından tüm ürünleri al
    all_products = mycol.find()

    # Tabloyu veritabanı ürünleri ile doldur
    for product in all_products:
        title = product['title']
        price = product['price']
        tree.insert("", "end", values=(title, price))

# Ağaç görünümünü sıralamak için işlev
def sort_treeview(tree, column, reverse):
    # Sıralanacak sütundan veriyi al
    data = [(tree.set(item, column), item) for item in tree.get_children('')]

    # Veriyi yerinde sırala
    data.sort(reverse=reverse)

    for index, (val, item) in enumerate(data):
        tree.move(item, '', index)

        # Bir sonraki tıklama için sıralama sırasını tersine çevir
    tree.heading(column, command=lambda: sort_treeview(tree, column, not reverse))

# Arama işlevini tanımla
def search_products():
    keyword = search_entry.get().strip().lower()  # Girilen kelimeyi al ve küçük harfe çevir
    if keyword:
        listbox.delete(0, END)  # Mevcut ürünleri temizle

        # Tüm ürünleri al ve anahtar kelimeye göre filtrele
        all_products = mycol.find()
        for product in all_products:
            title = product['title'].lower()  # Başlığı küçük harfe çevir
            if keyword in title:
                listbox.insert(END, f"Başlık: {product['title']}, Fiyat: {product['price']}")

# Arama düğmesini ekle
search_button = tk.Button(root, text="Ürün Ara", command=search_products)
search_button.pack(pady=5)

# Ana GUI penceresini oluştur
root = tk.Tk()
root.title("Amazon Ürün Takip Botu")

# Pencere arka plan rengini ayarla
root.configure(bg="lightgray")

# Ürün bilgilerini görüntülemek için bir liste kutusu oluştur
listbox = Listbox(root, width=80, height=20)
scrollbar = Scrollbar(root)
listbox.config(yscrollcommand=scrollbar.set)

scrollbar.config(command=listbox.yview)

listbox.pack(side=tk.LEFT, padx=10, pady=10)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Çeşitli işlemler için düğmeler oluştur
update_button = tk.Button(root, text="Ürünleri Güncelle", command=update_listbox)
update_button.pack(pady=10)

show_all_button = tk.Button(root, text="Tüm Ürünleri Göster", command=show_all_products)
show_all_button.pack(pady=10)

add_product_button = tk.Button(root, text="Ürün Ekle", command=add_product_window)
add_product_button.pack(pady=10)

# Arama kutusunu ekle
search_entry = tk.Entry(root, width=30)
search_entry.pack(pady=10)

# Arama düğmesini ekle
search_button = tk.Button(root, text="Ürün Ara", command=search_products)
search_button.pack(pady=5)

# Ürün verilerini bir tabloda görüntülemek için bir ağaç görünümü oluştur
tree = ttk.Treeview(root, columns=("Title", "Price", "İndirim"), show="headings")
tree.heading("Title", text="Başlık")
tree.heading("Price", text="Fiyat")
tree.heading("İndirim", text="İndirim")

# Sıralama için düğmeler oluştur
title_sort_button = tk.Button(root, text="Başlığa Göre Sırala", command=lambda: sort_treeview(tree, "Title", True))
price_sort_button = tk.Button(root, text="Fiyata Göre Sırala", command=lambda: sort_treeview(tree, "Price", False))

tree.pack(padx=10, pady=10)
title_sort_button.pack(pady=5)
price_sort_button.pack(pady=5)

# Tabloyu ürün verileri ile doldur
display_data()

# Arama kutusuna Enter tuşu bağlama
search_entry.bind("<Return>", lambda event=None: search_products())

# GUI ana döngüsünü çalıştır
root.mainloop()
