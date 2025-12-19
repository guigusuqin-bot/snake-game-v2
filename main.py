# -*- coding: utf-8 -*-
import os
import random

from kivy.app import App
from kivy.core.text import LabelBase
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget


APP_TITLE = "星座对打"
ASSETS_DIR = "assets"

# 你可以把字体放在以下任意一个位置，程序会自动尝试加载（找不到也不会崩）
FONT_CANDIDATES = [
    os.path.join(ASSETS_DIR, "NotoSansSC-VariableFont_wght.ttf"),
    os.path.join(ASSETS_DIR, "NotoSansSC-Regular.ttf"),
    "NotoSansSC-VariableFont_wght.ttf",  # 你现在仓库根目录有的话也能尝试
]

ZODIACS = [
    "白羊座", "金牛座", "双子座", "巨蟹座",
    "狮子座", "处女座", "天秤座", "天蝎座",
    "射手座", "摩羯座", "水瓶座", "双鱼座"
]


def try_register_chinese_font():
    """
    不炸兜底：找到字体就注册为 'CN'；找不到就跳过。
    """
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                LabelBase.register(name="CN", fn_regular=p)
                return True, p
            except Exception:
                pass
    return False, ""


def make_label(text, font_ok=False, **kwargs):
    # font_ok=True 才强制用中文字体，否则使用系统默认字体（不崩但可能不显示中文）
    if font_ok:
        kwargs.setdefault("font_name", "CN")
    return Label(text=text, **kwargs)


class HomeScreen(Screen):
    def __init__(self, font_ok=False, **kwargs):
        super().__init__(**kwargs)
        self.font_ok = font_ok

        root = BoxLayout(orientation="vertical", padding=16, spacing=12)

        title = make_label(APP_TITLE, font_ok=self.font_ok, font_size="26sp", size_hint_y=None, height=60)
        tip = make_label("点击开始 → 选择你的星座", font_ok=self.font_ok, font_size="16sp", size_hint_y=None, height=40)

        btn = Button(text="开始游戏", size_hint_y=None, height=56)
        btn.bind(on_release=lambda *_: self.go_next())

        root.add_widget(Widget(size_hint_y=1))
        root.add_widget(title)
        root.add_widget(tip)
        root.add_widget(btn)
        root.add_widget(Widget(size_hint_y=1))

        self.add_widget(root)

    def go_next(self):
        self.manager.current = "select"


class SelectScreen(Screen):
    def __init__(self, font_ok=False, **kwargs):
        super().__init__(**kwargs)
        self.font_ok = font_ok

        root = BoxLayout(orientation="vertical", padding=12, spacing=10)

        header = make_label("选择你的星座", font_ok=self.font_ok, font_size="22sp", size_hint_y=None, height=54)
        root.add_widget(header)

        grid = GridLayout(cols=3, spacing=8, size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        for name in ZODIACS:
            b = Button(text=name, size_hint_y=None, height=56)
            b.bind(on_release=self.on_pick)
            grid.add_widget(b)

        sv = ScrollView()
        sv.add_widget(grid)

        root.add_widget(sv)

        back = Button(text="返回", size_hint_y=None, height=50)
        back.bind(on_release=lambda *_: self.go_back())
        root.add_widget(back)

        self.add_widget(root)

    def on_pick(self, btn):
        me = btn.text
        enemy = random.choice([z for z in ZODIACS if z != me])
        self.manager.get_screen("battle").start_new_game(me, enemy)
        self.manager.current = "battle"

    def go_back(self):
        self.manager.current = "home"


class BattleScreen(Screen):
    def __init__(self, font_ok=False, **kwargs):
        super().__init__(**kwargs)
        self.font_ok = font_ok

        # 状态
        self.me = ""
        self.enemy = ""
        self.me_hp = 100
        self.enemy_hp = 100
        self.game_over = False

        # UI
        root = BoxLayout(orientation="vertical", padding=12, spacing=10)

        self.title_lbl = make_label("", font_ok=self.font_ok, font_size="20sp", size_hint_y=None, height=48)
        root.add_widget(self.title_lbl)

        self.hp_lbl = make_label("", font_ok=self.font_ok, font_size="16sp", size_hint_y=None, height=40)
        root.add_widget(self.hp_lbl)

        self.log_lbl = make_label("", font_ok=self.font_ok, font_size="15sp")
        root.add_widget(self.log_lbl)

        self.attack_btn = Button(text="普通攻击", size_hint_y=None, height=56)
        self.attack_btn.bind(on_release=lambda *_: self.on_attack())
        root.add_widget(self.attack_btn)

        bottom = BoxLayout(size_hint_y=None, height=50, spacing=10)
        self.restart_btn = Button(text="再来一局", disabled=True)
        self.restart_btn.bind(on_release=lambda *_: self.restart())
        self.back_btn = Button(text="回到选择")
        self.back_btn.bind(on_release=lambda *_: self.back_to_select())
        bottom.add_widget(self.restart_btn)
        bottom.add_widget(self.back_btn)

        root.add_widget(bottom)

        self.add_widget(root)

        self.refresh_ui("")

    def start_new_game(self, me, enemy):
        self.me = me
        self.enemy = enemy
        self.me_hp = 100
        self.enemy_hp = 100
        self.game_over = False
        self.attack_btn.disabled = False
        self.restart_btn.disabled = True
        self.refresh_ui("战斗开始！点击【普通攻击】")

    def refresh_ui(self, log):
        self.title_lbl.text = f"{self.me}  VS  {self.enemy}"
        self.hp_lbl.text = f"你 HP: {self.me_hp}    对手 HP: {self.enemy_hp}"
        self.log_lbl.text = log

    def on_attack(self):
        if self.game_over:
            return

        # 你打
        dmg_me = random.randint(8, 15)
        self.enemy_hp = max(0, self.enemy_hp - dmg_me)

        if self.enemy_hp == 0:
            self.game_over = True
            self.attack_btn.disabled = True
            self.restart_btn.disabled = False
            self.refresh_ui(f"你造成 {dmg_me} 伤害！\n对手倒下了！✅你赢了")
            return

        # 电脑反击
        dmg_enemy = random.randint(7, 14)
        self.me_hp = max(0, self.me_hp - dmg_enemy)

        if self.me_hp == 0:
            self.game_over = True
            self.attack_btn.disabled = True
            self.restart_btn.disabled = False
            self.refresh_ui(f"你造成 {dmg_me} 伤害！\n对手反击造成 {dmg_enemy} 伤害！\n你倒下了… ❌你输了")
            return

        self.refresh_ui(f"你造成 {dmg_me} 伤害！\n对手反击造成 {dmg_enemy} 伤害！")

    def restart(self):
        if not self.me or not self.enemy:
            return
        self.start_new_game(self.me, self.enemy)

    def back_to_select(self):
        self.manager.current = "select"


class ZodiacFightApp(App):
    def build(self):
        font_ok, font_path = try_register_chinese_font()

        sm = ScreenManager()
        sm.add_widget(HomeScreen(name="home", font_ok=font_ok))
        sm.add_widget(SelectScreen(name="select", font_ok=font_ok))
        sm.add_widget(BattleScreen(name="battle", font_ok=font_ok))

        # 如果你想临时确认是否加载到字体，可把下面一行解开（不影响逻辑）
        # print("FONT_OK:", font_ok, "FONT_PATH:", font_path)

        return sm


if __name__ == "__main__":
    ZodiacFightApp().run()
