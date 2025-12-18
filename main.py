import random

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button


# =========================
# 跑不炸优先：所有关键点都 try/if 防御
# =========================

GRID_W = 18
GRID_H = 28
TICK_SEC = 0.14  # 速度：越小越快。稳定优先，别太小。


class StartScreen(FloatLayout):
    def __init__(self, on_start, **kwargs):
        super().__init__(**kwargs)
        self.on_start = on_start

        title = Label(
            text="欢迎静静来到我的世界！",
            font_size="22sp",
            size_hint=(1, None),
            height=dp(60),
            pos_hint={"center_x": 0.5, "top": 0.95},
        )
        self.add_widget(title)

        btn = Button(
            text="开始",
            font_size="20sp",
            size_hint=(0.6, None),
            height=dp(56),
            pos_hint={"center_x": 0.5, "center_y": 0.45},
        )
        btn.bind(on_release=lambda *_: self.safe_start())
        self.add_widget(btn)

        tip = Label(
            text="（跑不炸优先版）",
            font_size="14sp",
            size_hint=(1, None),
            height=dp(30),
            pos_hint={"center_x": 0.5, "y": 0.15},
        )
        self.add_widget(tip)

    def safe_start(self):
        try:
            self.on_start()
        except Exception:
            # 不让任何异常导致闪退
            pass


class SnakeBoard(GridLayout):
    """
    简化渲染：用 GridLayout + Button 当像素块（最稳定）
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = GRID_W
        self.rows = GRID_H
        self.spacing = 0
        self.padding = 0
        self.size_hint = (1, 1)

        self.cells = []
        for _ in range(GRID_W * GRID_H):
            c = Label(text="")  # Label 更轻；不用按钮避免点击事件干扰
            self.cells.append(c)
            self.add_widget(c)

    def draw(self, snake, food, dead=False):
        try:
            # 清空
            for c in self.cells:
                c.text = ""
            # 画食物
            fx, fy = food
            self._set_cell(fx, fy, "🍎")
            # 画蛇
            for i, (x, y) in enumerate(snake):
                self._set_cell(x, y, "🟩" if i == 0 else "🟢")
            if dead:
                # 不额外复杂处理，保持稳定
                pass
        except Exception:
            # 任何绘制异常都不炸
            pass

    def _set_cell(self, x, y, text):
        if 0 <= x < GRID_W and 0 <= y < GRID_H:
            idx = (GRID_H - 1 - y) * GRID_W + x  # y 反转让底部是 y=0
            if 0 <= idx < len(self.cells):
                self.cells[idx].text = text


class GameScreen(FloatLayout):
    def __init__(self, on_quit_to_start, play_bgm, stop_bgm, **kwargs):
        super().__init__(**kwargs)
        self.on_quit_to_start = on_quit_to_start
        self.play_bgm = play_bgm
        self.stop_bgm = stop_bgm

        self.board = SnakeBoard(size_hint=(1, 0.78), pos_hint={"x": 0, "top": 1})
        self.add_widget(self.board)

        self.info = Label(
            text="得分：0",
            size_hint=(1, None),
            height=dp(36),
            pos_hint={"x": 0, "y": 0.20},
            font_size="16sp",
        )
        self.add_widget(self.info)

        # 控制区（方向键）
        self.ctrl = BoxLayout(
            orientation="vertical",
            size_hint=(1, 0.20),
            pos_hint={"x": 0, "y": 0},
            padding=[dp(10), dp(6), dp(10), dp(6)],
            spacing=dp(6),
        )
        self.add_widget(self.ctrl)

        # 上
        row1 = BoxLayout(size_hint=(1, 0.45), spacing=dp(6))
        row1.add_widget(Label(size_hint=(0.33, 1)))
        btn_up = Button(text="↑", font_size="22sp")
        btn_up.bind(on_release=lambda *_: self.set_dir(0, 1))
        row1.add_widget(btn_up)
        row1.add_widget(Label(size_hint=(0.33, 1)))
        self.ctrl.add_widget(row1)

        # 左 中 右
        row2 = BoxLayout(size_hint=(1, 0.55), spacing=dp(6))
        btn_left = Button(text="←", font_size="22sp")
        btn_left.bind(on_release=lambda *_: self.set_dir(-1, 0))
        btn_down = Button(text="↓", font_size="22sp")
        btn_down.bind(on_release=lambda *_: self.set_dir(0, -1))
        btn_right = Button(text="→", font_size="22sp")
        btn_right.bind(on_release=lambda *_: self.set_dir(1, 0))
        row2.add_widget(btn_left)
        row2.add_widget(btn_down)
        row2.add_widget(btn_right)
        self.ctrl.add_widget(row2)

        # 失败遮罩层
        self.overlay = FloatLayout(size_hint=(1, 1), opacity=0)
        self.add_widget(self.overlay)

        self.fail_text = Label(
            text="我想静静！",
            font_size="28sp",
            size_hint=(1, None),
            height=dp(60),
            pos_hint={"center_x": 0.5, "center_y": 0.62},
        )
        self.overlay.add_widget(self.fail_text)

        self.btn_restart = Button(
            text="再来一次",
            size_hint=(0.6, None),
            height=dp(50),
            pos_hint={"center_x": 0.5, "center_y": 0.45},
        )
        self.btn_restart.bind(on_release=lambda *_: self.safe_restart())
        self.overlay.add_widget(self.btn_restart)

        self.btn_back = Button(
            text="返回开始界面",
            size_hint=(0.6, None),
            height=dp(50),
            pos_hint={"center_x": 0.5, "center_y": 0.33},
        )
        self.btn_back.bind(on_release=lambda *_: self.safe_back())
        self.overlay.add_widget(self.btn_back)

        # 游戏状态
        self._event = None
        self.reset()

    def on_enter(self):
        # 进入游戏就播放 BGM（找不到也不炸）
        try:
            self.play_bgm()
        except Exception:
            pass

        # 启动 tick
        self._event = Clock.schedule_interval(lambda dt: self.tick(), TICK_SEC)

    def on_leave(self):
        try:
            if self._event:
                self._event.cancel()
                self._event = None
        except Exception:
            pass

    def reset(self):
        self.score = 0
        self.dead = False
        self.dir = (0, 1)  # 默认向上
        cx, cy = GRID_W // 2, GRID_H // 2
        self.snake = [(cx, cy), (cx, cy - 1), (cx, cy - 2)]
        self.food = self.spawn_food()
        self.update_ui()
        self.hide_overlay()
        self.board.draw(self.snake, self.food)

    def spawn_food(self):
        # 防御：最多尝试 N 次，避免死循环
        for _ in range(500):
            x = random.randint(0, GRID_W - 1)
            y = random.randint(0, GRID_H - 1)
            if (x, y) not in self.snake:
                return (x, y)
        # 实在找不到：给个固定点，也不炸
        return (0, 0)

    def set_dir(self, dx, dy):
        # 防止 180 度反向导致瞬间自撞（更稳）
        try:
            if self.dead:
                return
            cur_dx, cur_dy = self.dir
            if (dx, dy) == (-cur_dx, -cur_dy):
                return
            self.dir = (dx, dy)
        except Exception:
            pass

    def tick(self):
        if self.dead:
            return

        try:
            dx, dy = self.dir
            head_x, head_y = self.snake[0]
            nx, ny = head_x + dx, head_y + dy

            # 撞墙
            if nx < 0 or nx >= GRID_W or ny < 0 or ny >= GRID_H:
                self.game_over()
                return

            # 撞自己（允许尾巴移动的情况：先算是否吃到食物）
            eating = (nx, ny) == self.food
            new_snake = [(nx, ny)] + self.snake

            if not eating:
                new_snake.pop()  # 不吃就移除尾巴

            # 自撞检测
            if (nx, ny) in new_snake[1:]:
                self.game_over()
                return

            self.snake = new_snake

            if eating:
                self.score += 1
                self.food = self.spawn_food()

            self.update_ui()
            self.board.draw(self.snake, self.food)

        except Exception:
            # 任何异常直接结束但不闪退
            self.game_over()

    def update_ui(self):
        try:
            self.info.text = f"得分：{self.score}"
        except Exception:
            pass

    def game_over(self):
        self.dead = True
        try:
            self.board.draw(self.snake, self.food, dead=True)
        except Exception:
            pass
        self.show_overlay()

    def show_overlay(self):
        try:
            self.overlay.opacity = 1
        except Exception:
            pass

    def hide_overlay(self):
        try:
            self.overlay.opacity = 0
        except Exception:
            pass

    def safe_restart(self):
        try:
            self.reset()
        except Exception:
            # 最坏情况也回到开始界面
            self.safe_back()

    def safe_back(self):
        try:
            self.stop_bgm()
        except Exception:
            pass
        try:
            self.on_quit_to_start()
        except Exception:
            pass


class SnakeApp(App):
    def build(self):
        self.sound = None
        self.root_layout = FloatLayout()

        self.start_screen = StartScreen(on_start=self.go_game)
        self.root_layout.add_widget(self.start_screen)

        # 游戏界面先不加，开始后再切换
        self.game_screen = None

        return self.root_layout

    # ===== BGM 安全播放（找不到也不炸）=====
    def play_bgm(self):
        try:
            if self.sound is None:
                self.sound = SoundLoader.load("bgm.mp3")
            if self.sound:
                self.sound.loop = True
                self.sound.volume = 0.4
                self.sound.play()
        except Exception:
            pass

    def stop_bgm(self):
        try:
            if self.sound:
                self.sound.stop()
        except Exception:
            pass

    # ===== 界面切换 =====
    def go_game(self):
        try:
            self.root_layout.clear_widgets()
        except Exception:
            pass

        self.game_screen = GameScreen(
            on_quit_to_start=self.go_start,
            play_bgm=self.play_bgm,
            stop_bgm=self.stop_bgm,
        )
        self.root_layout.add_widget(self.game_screen)
        # 进入后启动
        try:
            self.game_screen.on_enter()
        except Exception:
            pass

    def go_start(self):
        try:
            if self.game_screen:
                self.game_screen.on_leave()
        except Exception:
            pass

        try:
            self.root_layout.clear_widgets()
        except Exception:
            pass

        self.start_screen = StartScreen(on_start=self.go_game)
        self.root_layout.add_widget(self.start_screen)


if __name__ == "__main__":
    SnakeApp().run()
