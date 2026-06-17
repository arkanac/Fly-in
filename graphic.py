try:
    import pygame
except ImportError as e:
    raise (e)


class Display:
    def __init__(self, graph):
        self.graph = graph
        self.running = True
        self.middle = []
    
    def coordinate_calculation(self, surface):
        max_y = max(self.graph.zones.values(), key=lambda zone: zone.y).y
        max_x = max(self.graph.zones.values(), key=lambda zone: zone.x).x
        min_y = min(self.graph.zones.values(), key=lambda zone: zone.y).y
        min_x = min(self.graph.zones.values(), key=lambda zone: zone.x).x
        x_amplitude = max_x - min_x
        y_amplitude = max_y - min_y
        middle_x = (min_x + max_x) / 2
        middle_y = (min_y + max_y) / 2




    def show_smg(self):
        pygame.init()
        pygame.display.set_mode()
        s = pygame.display.get_surface()
        print(s)
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            pygame.display.flip()
            pygame.draw.circle(s,  "blue", [250, 250], 40, 0)
        pygame.quit()
