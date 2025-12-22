from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.core.audio import SoundLoader
from kivy.resources import resource_find
from kivy.core.text import LabelBase
from kivy.metrics import dp


class MusicOneButtonApp(App):
    def build(self):
        # ========= 1) 字体：保证中文正常显示 =========
        font_path = resource_find("NotoSansSC-VariableFont_wght.ttf")
        if font_path:
            LabelBase.register(name="CN", fn_regular=font_path)
            self.cn_font = "CN"
        else:
            # 找不到字体也不崩，但中文可能变方块
            self.cn_font = None
            print("❌ 未找到字体：NotoSansSC-VariableFont_wght.ttf")

        # ========= 2) 资源路径：背景图（3张循环） =========
        self.bg_paths = [
            resource_find("assets/bg_1.png"),
            resource_find("assets/bg_2.png"),
            resource_find("assets/bg_3.png"),
        ]
        # 过滤掉 None（避免崩溃）
        self.bg_paths = [p for p in self.bg_paths if p]

        if not self.bg_paths:
            print("❌ 未找到任何背景图：assets/bg_1.png/bg_2.png/bg_3.png")

        self.bg_index = 0

        # ========= 3) 音频：不自动播放，只在点击时播放 =========
        self.sound = None
        self.is_playing = False

        # ========= 4) UI =========
        root = FloatLayout()

        # 背景图铺满
        self.bg = Image(
            source=self.bg_paths[self.bg_index] if self.bg_paths else "",
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        root.add_widget(self.bg)

        # 一个按钮：切歌（同时切背景、切播放状态）
        self.btn = Button(
            text="切歌",
            font_name=self.cn_font if self.cn_font else None,
            font_size=dp(28),
            size_hint=(None, None),
            size=(dp(180), dp(90)),
            pos_hint={"center_x": 0.5, "center_y": 0.25},
        )
        self.btn.bind(on_press=self.on_switch)
        root.add_widget(self.btn)

        return root

    def on_switch(self, _):
        """
        点击一次：
        1) 切换背景图（3张循环）
        2) 音乐：若没播则开始播；若在播则停止（等于“切歌/切状态”）
        """
        # ---- 切背景 ----
        if self.bg_paths:
            self.bg_index = (self.bg_index + 1) % len(self.bg_paths)
            self.bg.source = self.bg_paths[self.bg_index]
            self.bg.reload()

        # ---- 音频切换（无自动播放，完全由点击触发）----
        mp3_path = resource_find("bgm.mp3")
        if not mp3_path:
            print("❌ 未找到 bgm.mp3")
            return

        # 首次加载
        if self.sound is None:
            self.sound = SoundLoader.load(mp3_path)
            if not self.sound:
                print("❌ bgm.mp3 加载失败")
                return

        # 播放/停止切换
        if self.is_playing:
            self.sound.stop()
            self.is_playing = False
        else:
            self.sound.play()
            self.is_playing = True


if __name__ == "__main__":
    MusicOneButtonApp().run()
