#!/usr/bin/env python3
"""Project actual static collision footprints into a navigation map."""
from pathlib import Path
import math
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
HALL=ROOT.parent/'heritage_hall'
RES=.05
ORIGIN=(-19.,-13.)
SIZE=(760,520)


def footprints():
    for model in ET.parse(HALL/'worlds/heritage_hall.sdf').getroot().findall('world/model'):
        for collision in model.findall('link/collision'):
            pose=list(map(float,collision.findtext('pose','0 0 0 0 0 0').split()))
            box=collision.find('geometry/box')
            cylinder=collision.find('geometry/cylinder')
            if box is not None:
                sx,sy,sz=map(float,box.findtext('size').split())
                if pose[2]+sz/2<=.12 or pose[2]-sz/2>=1.55:
                    continue
                c,s=math.cos(pose[5]),math.sin(pose[5])
                yield [(pose[0]+c*x-s*y,pose[1]+s*x+c*y) for x,y in [(-sx/2,-sy/2),(sx/2,-sy/2),(sx/2,sy/2),(-sx/2,sy/2)]]
            elif cylinder is not None:
                radius=float(cylinder.findtext('radius'))
                height=float(cylinder.findtext('length'))
                if pose[2]+height/2<=.12 or pose[2]-height/2>=1.55:
                    continue
                yield [(pose[0]+radius*math.cos(a*math.tau/48),pose[1]+radius*math.sin(a*math.tau/48)) for a in range(48)]


def build():
    directory=ROOT/'maps';directory.mkdir(parents=True,exist_ok=True)
    im=Image.new('L',SIZE,0);d=ImageDraw.Draw(im)
    def pixel(x,y):return ((x-ORIGIN[0])/RES,SIZE[1]-(y-ORIGIN[1])/RES)
    d.rectangle([pixel(-17.7,11),pixel(17.7,-11)],fill=254)
    for x in (-12.5,9.4):d.rectangle([pixel(x-1.4,-11),pixel(x+1.4,-12.6)],fill=254)
    shapes=list(footprints())
    for points in shapes:d.polygon([pixel(x,y) for x,y in points],fill=0)
    im.save(directory/'hall.pgm')
    (directory/'hall.yaml').write_text('image: hall.pgm\nmode: trinary\nresolution: 0.05\norigin: [-19.0, -13.0, 0.0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n',encoding='utf-8')
    preview=Image.open(HALL/'materials/textures/floor.png').convert('RGB').resize((1062,660))
    draw=ImageDraw.Draw(preview)
    for points in shapes:
        draw.polygon([((x+17.7)*30,(11-y)*30) for x,y in points],fill='#6c675f')
    preview.save(directory/'map.png')
    print(f'Generated collision map {SIZE}, resolution {RES} m')


if __name__=='__main__':build()
