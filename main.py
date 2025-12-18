from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
import random


class SnakeGame(Widget):
    """
    设计原则：跑不炸优先（只用 Kivy 原生组件 + 简单逻辑）
    功能：
    - 开始/游戏中/结束 三态
    - 滑动控制方向（手机友好）
    - 分数显示
    - 速度随分数提升（有上限，避免失控）
    """

    GRID = 18  # 网格数量（越大越细；越小越稳）

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # UI：顶部状态栏
        self.hud = Label(
            text="Snake | 点击开始 / Swipe 控制方向",
            size_hint=(1, None),
            height=dp(44),
            halign="left",
            valign="middle",
        )
        self.hud.bind(size=self._update_hud_text_alignment)
        self.add_widget(self.hud)

        # 颜色（尽量简单）
        self.bg_color = (0.06, 0.06, 0.07, 1)
        self.snake_color = (0.3, 0.9, 0.5, 1)
        self.head_color = (0.2, 1.0, 0.6, 1)
        self.food_color = (1.0, 0.35, 0.35, 1)

        # 状态
        self.state = "ready"  # ready / running / over
        self.score = 0

        # 游戏数据
        self.cell = 1
        self.board_size = 1
        self.board_x = 0
        self.board_y = 0
        self.cols = self.GRID
        self.rows = self.GRID

        self.snake = []
        self.direction = (1, 0)     # 当前方向
        self.next_direction = (1, 0)  # 下一步方向（防止同一帧多次反转）
        self.food = (0, 0)

        # 触摸滑动记录
        self._touch_start = None

        # 定时器
        self.base_interval = 0.20   # 初始速度（秒/步）
        self.min_interval = 0.08    # 最快速度（防止炸）
        self.speed_step = 0.01      # 每次提速幅度
        self.speed_every = 3        # 每吃 N 分提速一次
        self._event = None

        # 画布对象缓存（避免反复创建导致卡顿）
        self._rects = []
        self._food_rect = None
        self._bg_rect = None

        # 监听大小变化
        Window.bind(on_resize=lambda *_: self._layout())

        # 初次布局&绘制
        Clock.schedule_once(lambda *_: self._reset_game(draw_only=True), 0)

    def _update_hud_text_alignment(self, *_):
        self.hud.text_size = (self.hud.width - dp(12), self.hud.height)

    def _layout(self):
        # HUD 放顶部
        self.hud.pos = (0, self.height - self.hud.height)

        # 棋盘区域（HUD 下方）
        margin = dp(10)
        usable_w = max(1, self.width - 2 * margin)
        usable_h = max(1, self.height - self.hud.height - 2 * margin)

        self.board_size = int(min(usable_w, usable_h))
        self.board_x = int((self.width - self.board_size) / 2)
        self.board_y = int((self.height - self.hud.height - self.board_size) / 2)

        # cell 像素大小
        self.cell = max(1, int(self.board_size / self.GRID))

        # 根据 cell 重新确定棋盘像素大小（对齐像素，避免抖动）
        self.board_size = self.cell * self.GRID

        # 背景矩形
        if self._bg_rect is None:
            with self.canvas.before:
                Color(*self.bg_color)
                self._bg_rect = Rectangle(pos=(self.board_x, self.board_y), size=(self.board_size, self.board_size))
        else:
            self._bg_rect.pos = (self.board_x, self.board_y)
            self._bg_rect.size = (self.board_size, self.board_size)

        # 重画一次
        self._draw()

    def _reset_game(self, draw_only=False):
        # 初始化布局（确保棋盘尺寸正确）
        self._layout()

        if draw_only:
            return

        self.state = "ready"
        self.score = 0
        self.direction = (1, 0)
        self.next_direction = (1, 0)

        # 初始蛇：长度 3，居中
        mid = self.GRID // 2
        self.snake = [(mid - 1, mid), (mid, mid), (mid + 1, mid)]
        self._spawn_food()

        self._set_hud("Snake | 点击开始 / Swipe 控制方向")
        self._stop_loop()
        self._draw()

    def _set_hud(self, msg):
        self.hud.text = f"{msg}    分数: {self.score}"

    def _spawn_food(self):
        # 避免食物刷在蛇身上
        occupied = set(self.snake)
        tries = 0
        while True:
            tries += 1
            if tries > 500:
                # 极端情况下兜底（理论不会发生）
                self.food = (0, 0)
                return
            fx = random.randrange(0, self.GRID)
            fy = random.randrange(0, self.GRID)
            if (fx, fy) not in occupied:
                self.food = (fx, fy)
                return

    def _start_loop(self):
        if self._event is not None:
            return
        interval = self._calc_interval()
        self._event = Clock.schedule_interval(self._tick, interval)

    def _restart_loop_with_new_speed(self):
        # 提速后重启定时器（Kivy schedule_interval 不支持动态改 interval）
        self._stop_loop()
        self._start_loop()

    def _stop_loop(self):
        if self._event is not None:
            self._event.cancel()
            self._event = None

    def _calc_interval(self):
        # 每吃 speed_every 分提速一次
        steps = self.score // self.speed_every
        interval = self.base_interval - steps * self.speed_step
        if interval < self.min_interval:
            interval = self.min_interval
        return interval

    def on_touch_down(self, touch):
        # 触摸开始位置用于判断滑动方向
        self._touch_start = (touch.x, touch.y)
        return True

    def on_touch_up(self, touch):
        # 处理点击开始 / 再来一局
        if self.state in ("ready", "over"):
            # 轻点开始 / 重开
            self.state = "running"
            if self.state == "running" and self._event is None:
                self._set_hud("运行中 | Swipe 控制方向")
                self._start_loop()
            self._touch_start = None
            return True

        # 游戏中：判断滑动方向
        if self._touch_start is None:
            return True

        sx, sy = self._touch_start
        dx = touch.x - sx
        dy = touch.y - sy
        self._touch_start = None

        # 滑动阈值，防误触
        threshold = dp(18)
        if abs(dx) < threshold and abs(dy) < threshold:
            return True

        # 横向优先 / 纵向优先
        if abs(dx) > abs(dy):
            # 左右
            if dx > 0:
                self._request_direction((1, 0))
            else:
                self._request_direction((-1, 0))
        else:
            # 上下
            if dy > 0:
                self._request_direction((0, 1))
            else:
                self._request_direction((0, -1))
        return True

    def _request_direction(self, d):
        # 防止 180 度反向（会立刻撞自己）
        cx, cy = self.direction
        nx, ny = d
        if (cx + nx == 0) and (cy + ny == 0):
            return
        self.next_direction = d

    def _tick(self, _dt):
        if self.state != "running":
            return

        # 只在 tick 开始时采纳 next_direction，避免一帧多次改变
        self.direction = self.next_direction

        head_x, head_y = self.snake[-1]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        # 撞墙
        if not (0 <= new_head[0] < self.GRID and 0 <= new_head[1] < self.GRID):
            self._game_over("撞墙了")
            return

        # 撞自己（允许尾巴先移动：先判断是否吃到食物）
        ate = (new_head == self.food)
        body = self.snake[1:] if not ate else self.snake  # 吃到就不去尾巴，判定更严格
        if new_head in body:
            self._game_over("撞到自己")
            return

        # 前进
        self.snake.append(new_head)

        if ate:
            self.score += 1
            self._spawn_food()
            self._set_hud("运行中 | Swipe 控制方向")

            # 提速：每到阈值就重启定时器
            if self.score % self.speed_every == 0:
                self._restart_loop_with_new_speed()
        else:
            # 不吃就去尾
            self.snake.pop(0)

        self._draw()

    def _game_over(self, reason):
        self.state = "over"
        self._stop_loop()
        self._set_hud(f"Game Over（{reason}）| 点一下重新开始")
        self._draw()

    def _cell_to_px(self, c):
        # 网格坐标 -> 像素坐标
        x = self.board_x + c[0] * self.cell
        y = self.board_y + c[1] * self.cell
        return (x, y)

    def _draw(self):
        # 确保布局存在
        if self.board_size <= 1:
            self._layout()

        # 清理旧 rects（只清 snake/food，不清背景）
        # 方式：把 rects 存起来，每次重用/重画，避免堆积
        # 简化：每次重新建也能跑，但这里尽量稳且不卡
        # 先移除旧的
        for r in self._rects:
            try:
                self.canvas.remove(r)
            except Exception:
                pass
        self._rects = []
        if self._food_rect is not None:
            try:
                self.canvas.remove(self._food_rect)
            except Exception:
                pass
            self._food_rect = None

        # 画食物
        fx, fy = self.food
        with self.canvas:
            Color(*self.food_color)
            self._food_rect = Rectangle(pos=self._cell_to_px((fx, fy)), size=(self.cell, self.cell))

        # 画蛇
        with self.canvas:
            for i, seg in enumerate(self.snake):
                if i == len(self.snake) - 1:
                    Color(*self.head_color)
                else:
                    Color(*self.snake_color)
                rect = Rectangle(pos=self._cell_to_px(seg), size=(self.cell, self.cell))
                self._rects.append(rect)


class SnakeApp(App):
    def build(self):
        Window.clearcolor = (0.05, 0.05, 0.06, 1)
        game = SnakeGame()
        # 初次启动
        Clock.schedule_once(lambda *_: game._reset_game(draw_only=False), 0)
        return game


if __name__ == "__main__":
    SnakeApp().run()
