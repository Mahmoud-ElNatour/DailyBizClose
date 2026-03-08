import json
import os
import decimal
from app import app
from models import db, MenuCategory, MenuItem

def import_data(json_file_path):
    if not os.path.exists(json_file_path):
        print(f"File not found: {json_file_path}")
        return

    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with app.app_context():
        print("Clearing existing menu data...")
        # Since MenuItem has category_id as foreign key with cascade,
        # deleting categories should delete items, but we can explicitly do both.
        MenuItem.query.delete()
        MenuCategory.query.delete()
        db.session.commit()

        print("Importing new menu data...")
        cat_sort_order = 1
        
        for category_data in data:
            cat_name = category_data.get('name', '').strip()
            if not cat_name:
                continue
                
            cat = MenuCategory(
                name=cat_name,
                description="",
                sort_order=cat_sort_order,
                is_active=True
            )
            db.session.add(cat)
            db.session.flush() # To get cat.id
            cat_sort_order += 1
            
            item_sort_order = 1
            items_data = category_data.get('items', [])
            
            for item_data in items_data:
                item_name = item_data.get('name', '').strip()
                if not item_name:
                    continue
                    
                price_val = item_data.get('price', 0.0)
                image_url = item_data.get('image', None)
                if image_url == "":
                    image_url = None
                    
                is_avail = item_data.get('is_available', True)
                
                item = MenuItem(
                    category_id=cat.id,
                    name=item_name,
                    description=item_data.get('description', ''),
                    price=decimal.Decimal(str(price_val)),
                    image_url=image_url,
                    is_available=is_avail,
                    sort_order=item_sort_order,
                    is_active=True
                )
                db.session.add(item)
                item_sort_order += 1

        db.session.commit()
        print("Menu imported successfully.")

if __name__ == '__main__':
    # Adjust path if script is run outside the workspace root
    json_path = r"C:\apps\DailyBizClose\menu_extracted.json"
    import_data(json_path)
