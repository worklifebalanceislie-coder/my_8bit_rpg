import pygame

class Movement:
    def __init__(self, owner, speed=60):
        self.owner = owner
        self.speed = speed
        self.pos_x = float(owner.rect.x)
        self.pos_y = float(owner.rect.y)
        self.is_moving = False
        self.walk_timer = 0.0

    def update(self, dt):
        if self.is_moving:
            self.walk_timer += dt * 10.0  # Скорость перебирания ногами
        else:
            self.walk_timer = 0.0
        # Сбрасываем флаг каждый кадр (если move не вызовут, персонаж стоит)
        self.is_moving = False

    def move(self, dx, dy, dt, walls):
        if getattr(self.owner, "effects", None):
            dt *= self.owner.effects.get_speed_multiplier()

        if dx == 0 and dy == 0:
            return

        self.is_moving = True

        if dx < 0:
            self.owner.facing_left = True
        elif dx > 0:
            self.owner.facing_left = False

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        self.owner.facing_dir = (dx, dy)


        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        self.pos_x += dx * self.speed * dt
        self.owner.rect.x = round(self.pos_x)
        for wall in walls:
            if self.owner.rect.colliderect(wall):
                if dx > 0:
                    self.owner.rect.right = wall.left
                elif dx < 0:
                    self.owner.rect.left = wall.right
                self.pos_x = float(self.owner.rect.x)

        self.pos_y += dy * self.speed * dt
        self.owner.rect.y = round(self.pos_y)
        for wall in walls:
            if self.owner.rect.colliderect(wall):
                if dy > 0:
                    self.owner.rect.bottom = wall.top
                elif dy < 0:
                    self.owner.rect.top = wall.bottom
                self.pos_y = float(self.owner.rect.y)
