from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.core.window import Window

# 方便预览（不影响手机实际运行）
Window.size = (360, 640)

# ========= 开始界面 =========
class StartScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = FloatLayout()

        start_button = Button(
            text="我爱你",
            font_size=48,
            size_hint=(0.75, 0.35),  # 大号按钮
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            background_normal="",
            background_color=(1, 0, 0, 1),  # 红色
            color=(1, 1, 1, 1),
        )

        start_button.bind(on_press=self.go_next)
        layout.add_widget(start_button)
        self.add_widget(layout)

    def go_next(self, instance):
        self.manager.current = "choice"


# ========= 第二个界面 =========
class ChoiceScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = FloatLayout()

        btn1 = Button(
            text="我爱褚少华",
            font_size=22,
            size_hint=(0.8, 0.15),
            pos_hint={"center_x": 0.5, "center_y": 0.65},
            background_normal="",
            background_color=(0.9, 0.2, 0.2, 1),
            color=(1, 1, 1, 1),
        )

        btn2 = Button(
            text="和褚少华度过余生",
            font_size=22,
            size_hint=(0.8, 0.15),
            pos_hint={"center_x": 0.5, "center_y": 0.45},
            background_normal="",
            background_color=(0.8, 0.1, 0.1, 1),
            color=(1, 1, 1, 1),
        )

        btn3 = Button(
            text="让褚少华给我 10 万美金",
            font_size=20,
            size_hint=(0.8, 0.15),
            pos_hint={"center_x": 0.5, "center_y": 0.25},
            background_normal="",
            background_color=(0.6, 0, 0, 1),
            color=(1, 1, 1, 1),
        )

        # 点击事件（现在只打印，不做现实行为）
        btn1.bind(on_press=lambda x: print("点击：我爱褚少华"))
        btn2.bind(on_press=lambda x: print("点击：和褚少华度过余生"))
        btn3.bind(on_press=lambda x: print("点击：让褚少华给我 10 万美金"))

        layout.add_widget(btn1)
        layout.add_widget(btn2)
        layout.add_widget(btn3)
        self.add_widget(layout)


# ========= App =========
class MyApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(StartScreen(name="start"))
        sm.add_widget(ChoiceScreen(name="choice"))
        return sm


if __name__ == "__main__":
    MyApp().run()
