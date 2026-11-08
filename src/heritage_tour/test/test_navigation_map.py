"""A tour stop must fit the whole robot, not just be inside a colored zone."""
import json
import math
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


def test_all_stops_have_collision_clearance():
    content=json.loads((ROOT/'config/content.json').read_text(encoding='utf-8'))
    image=Image.open(ROOT/'maps/hall.pgm')
    stops=[('home',content['home'])]+[(z['id'],z['pose']) for z in content['zones']]
    for name,(x,y,_) in stops:
        for radius in (0,.16,.32):
            for angle in range(36):
                px=x+radius*math.cos(angle*math.tau/36)
                py=y+radius*math.sin(angle*math.tau/36)
                pixel=(int((px+19)/.05),519-int((py+13)/.05))
                assert image.getpixel(pixel)>200,f'{name} overlaps a real exhibit/wall'
