from app import app, set_setting

# Define all default or existing settings here
settings_to_import = {
    'brand_name': 'Misk Beirut',
    'address': 'Ramlet L Baida, Beirut, Lebanon',
    'hours': 'Mon-Sun: 11:00 AM - 1:00 AM',
    'phone_display': '+961 76 551 204',
    'phone_tel': '+96176551204',
    'instagram_url': 'https://instagram.com/miskbeirut',
    'facebook_url': 'https://facebook.com/miskbeirut',
    'linkedin_url': '',
    'maps_url': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3312.46680034298!2d35.480399675169274!3d33.87762982693123!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x151f17aed3a8390f%3A0xdd3597ce3c491a6b!2sMisk%20beirut!5e0!3m2!1sen!2slb!4v1772749015216!5m2!1sen!2slb',
    'menu_url': ''
}

def import_all_settings():
    with app.app_context():
        print("Importing settings to the database...")
        for key, value in settings_to_import.items():
            success = set_setting(key, value)
            if success:
                print(f"Successfully imported setting: {key}")
            else:
                print(f"Failed to import setting: {key}")
                
        print("Settings import completed successfully!")

if __name__ == '__main__':
    import_all_settings()
