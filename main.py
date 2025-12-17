from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.graphics import Rectangle, Color
from kivy.core.window import Window
import random

GRID_SIZE = 20
WIDTH = 20
HEIGHT = 30


class SnakeGame(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.snake = [(10, 15)]
        self.direction = (1, 0)
        self.food = self.spawn_food()
        self.score = 0

        self.label = Label(
            text="Score: 0",
            size_hint=(None, None),
            size=(200, 40),
            pos=(10, Window.height - 50),
        )
        self.add_widget(self.label)

        Clock.schedule_interval(self.update, 0.2)
        Window.bind(on_key_down=self.on_key_down)

    def spawn_food(self):
        while True:
            pos = (random.randint(0, WIDTH - 1), random.randint(0, HEIGHT - 1))
            if pos not in self.snake:
                return pos

    def on_key_down(self, window, key, scancode, codepoint, modifier):
        if key == 273:   # Up
            self.direction = (0, 1)
        elif key == 274: # Down
            self.direction = (0, -1)
        elif key == 275: # Right
            self.direction = (1, 0)
        elif key == 276: # Left
            self.direction = (-1, 0)

    def update(self, dt):
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        if (
            new_head[0] < 0 or new_head[0] >= WIDTH or
            new_head[1] < 0 or new_head[1] >= HEIGHT or
            new_head in self.snake
        ):
            self.reset()
            return

        self.snake.insert(0, new_head)

        if new_head == self.food:
            self.score += 1
            self.label.text = f"Score: {self.score}"
            self.food = self.spawn_food()
        else:
            self.snake.pop()

        self.draw()

    def reset(self):
        self.snake = [(10, 15)]
        self.direction = (1, 0)
        self.food = self.spawn_food()
        self.score = 0
        self.label.text = "Score: 0"

    def draw(self):
        self.canvas.clear()
        with self.canvas:
            Color(0, 1, 0)
            for x, y in self.snake:
                Rectangle(pos=(x * GRID_SIZE, y * GRID_SIZE),
                          size=(GRID_SIZE, GRID_SIZE))

            Color(1, 0, 0)
            fx, fy = self.food
            Rectangle(pos=(fx * GRID_SIZE, fy * GRID_SIZE),
                      size=(GRID_SIZE, GRID_SIZE))


class SnakeApp(App):
    def build(self):
        Window.size = (WIDTH * GRID_SIZE, HEIGHT * GRID_SIZE)
        return SnakeGame()


if __name__ == "__main__":
    SnakeApp().run()
