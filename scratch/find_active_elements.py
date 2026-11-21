from bs4 import BeautifulSoup

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

print("All elements with class containing 'active':")
for el in soup.find_all(class_=lambda c: c and 'active' in c.split()):
    print(f"<{el.name} id='{el.get('id')}' class='{el.get('class')}'>")

print("\nAll modal-overlay elements:")
for el in soup.find_all(class_=lambda c: c and 'modal-overlay' in c.split()):
    print(f"<{el.name} id='{el.get('id')}' class='{el.get('class')}' style='{el.get('style')}'>")
