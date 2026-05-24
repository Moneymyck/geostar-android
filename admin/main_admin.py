from kivy.app import App
from kivy.uix.label import Label

class GeostarAdminApp(App):
    def build(self):
        return Label(text="GEOSTAR Admin")

if __name__ == "__main__":
    GeostarAdminApp().run()
