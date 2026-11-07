#!/usr/bin/env python3
"""Rebuild the image-derived SDF and floor artwork; no online assets needed."""
from pathlib import Path
import math
import xml.etree.ElementTree as E
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H = 35.4, 22.0
WOOD = '0.38 0.22 0.11 1'
GOLD = '0.72 0.51 0.25 1'
DARK = '0.14 0.16 0.16 1'
CREAM = '0.81 0.75 0.61 1'
GLASS = '0.48 0.72 0.78 1'


def sub(parent, tag, text=None, **attributes):
    node = E.SubElement(parent, tag, attributes)
    if text is not None:
        node.text = str(text)
    return node


def xy(px, py):
    return (px - 625.5) * W / 799, (280 - py) * H / 504


def artwork():
    """Floor is decorative only; the SDF slab supplies floor contact."""
    scale = 3
    im = Image.new('RGB', (799 * scale, 504 * scale), '#ada395')
    d = ImageDraw.Draw(im)

    def p(points):
        return [((x - 226) * scale, (y - 28) * scale) for x, y in points]

    zones = [
        ([(228, 112), (303, 112), (347, 194), (347, 397), (306, 436), (305, 531), (228, 531)], '#c5aa82'),
        ([(303, 29), (756, 29), (756, 126), (714, 141), (685, 178), (388, 181), (347, 194), (303, 112)], '#b4b993'),
        ([(385, 531), (385, 477), (415, 456), (478, 456), (499, 436), (686, 436), (710, 453), (762, 453), (790, 478), (790, 531)], '#8eafbb'),
        ([(717, 211), (744, 168), (788, 168), (832, 220), (933, 220), (933, 439), (882, 439), (857, 477), (790, 477), (762, 453), (710, 415)], '#b6a4bd'),
        ([(756, 29), (1024, 29), (1024, 439), (934, 439), (934, 220), (832, 220), (788, 168), (744, 168), (756, 126)], '#cba1aa'),
    ]
    for points, color in zones:
        d.polygon(p(points), fill=color)
        d.line(p(points + [points[0]]), fill='#d6c6a4', width=3)
    # Stone joints stay subtle beneath the zones and route markings.
    for x in range(226, 1025, 32):
        d.line(p([(x, 28), (x, 532)]), fill='#afa797', width=1)
    for y in range(28, 533, 32):
        d.line(p([(226, y), (1025, y)]), fill='#afa797', width=1)
    font_path = next((v for v in [
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        'C:/Windows/Fonts/msyh.ttc',
    ] if Path(v).exists()), None)

    def text(at, label, size=13, fill='#fff9e8'):
        font = ImageFont.truetype(font_path, size * scale) if font_path else ImageFont.load_default()
        d.text(p([at])[0], label, anchor='mm', font=font, fill=fill, stroke_width=1, stroke_fill='#74674e')

    text((280, 242), '① 非遗概览', 13)
    text((541, 94), '② 传统工艺制作技艺区', 14)
    text((597, 449), '③ 非遗代表性作品展示区', 12)
    text((832, 255), '④ 传承人与历史故事区', 12)
    text((875, 172), '⑤ 互动体验 / 文创延伸区', 12)
    text((325, 478), '导览起点', 9)
    text((344, 518), '入口', 12)
    text((831, 517), '出口', 12)
    text((260, 70), '储藏 / 设备', 8)
    text((918, 482), '卫生间', 8)
    text((989, 482), '储藏 / 设备', 8)
    route = [(344, 525), (365, 475), (373, 400), (373, 245), (381, 213), (405, 187), (679, 187), (720, 158), (777, 139)]
    branch = [(373, 407), (350, 438), (343, 465)]
    onward = [(373, 470), (407, 438), (685, 438), (710, 416), (755, 444), (805, 463), (833, 498), (833, 525)]
    for points in (route, branch, onward):
        for a, b in zip(points, points[1:]):
            length = math.dist(a, b)
            for k in range(0, int(length), 12):
                t, u = k / length, min(k + 7, length) / length
                d.line(p([(a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t),
                          (a[0] + (b[0]-a[0])*u, a[1] + (b[1]-a[1])*u)]), fill='#fff9e6', width=5)
    for cx, cy, angle in [(373, 265, -math.pi/2), (546, 187, 0), (769, 140, 0), (831, 511, math.pi/2)]:
        pts = [(cx + math.cos(angle)*10, cy + math.sin(angle)*10),
               (cx + math.cos(angle+2.45)*10, cy + math.sin(angle+2.45)*10),
               (cx + math.cos(angle-2.45)*10, cy + math.sin(angle-2.45)*10)]
        d.polygon(p(pts), fill='#fff9e6')
    (ROOT / 'materials/textures').mkdir(parents=True, exist_ok=True)
    im.save(ROOT / 'materials/textures/floor.png')
    (ROOT / 'meshes').mkdir(exist_ok=True)
    (ROOT / 'meshes/floor.dae').write_text('''<?xml version="1.0"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
<asset><created>2026-11-07T00:00:00</created><modified>2026-11-07T00:00:00</modified><unit meter="1" name="meter"/><up_axis>Z_UP</up_axis></asset>
<library_geometries><geometry id="floor"><mesh>
<source id="pos"><float_array id="pos-array" count="12">-17.7 -11 0 17.7 -11 0 17.7 11 0 -17.7 11 0</float_array><technique_common><accessor source="#pos-array" count="4" stride="3"><param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common></source>
<source id="uv"><float_array id="uv-array" count="8">0 0 1 0 1 1 0 1</float_array><technique_common><accessor source="#uv-array" count="4" stride="2"><param name="S" type="float"/><param name="T" type="float"/></accessor></technique_common></source>
<source id="norm"><float_array id="norm-array" count="3">0 0 1</float_array><technique_common><accessor source="#norm-array" count="1" stride="3"><param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common></source>
<vertices id="verts"><input semantic="POSITION" source="#pos"/></vertices>
<triangles count="2"><input semantic="VERTEX" source="#verts" offset="0"/><input semantic="TEXCOORD" source="#uv" offset="1" set="0"/><input semantic="NORMAL" source="#norm" offset="2"/><p>0 0 0 1 1 0 2 2 0 0 0 0 2 2 0 3 3 0</p></triangles>
</mesh></geometry></library_geometries>
<library_visual_scenes><visual_scene id="Scene"><node id="floor-node"><instance_geometry url="#floor"/></node></visual_scene></library_visual_scenes><scene><instance_visual_scene url="#Scene"/></scene></COLLADA>''', encoding='utf-8')


def build():
    sdf = E.Element('sdf', version='1.9')
    world = sub(sdf, 'world', name='heritage_hall')
    sub(world, 'gravity', '0 0 -9.81')
    physics = sub(world, 'physics', name='physics', type='ignored')
    sub(physics, 'max_step_size', '0.001')
    sub(physics, 'real_time_factor', '1')
    for filename, name in [('physics', 'Physics'), ('user-commands', 'UserCommands'), ('scene-broadcaster', 'SceneBroadcaster'), ('sensors', 'Sensors')]:
        plugin = sub(world, 'plugin', filename=f'gz-sim-{filename}-system', name=f'gz::sim::systems::{name}')
        if name == 'Sensors':
            sub(plugin, 'render_engine', 'ogre2')
    scene = sub(world, 'scene')
    sub(scene, 'ambient', '0.65 0.65 0.65 1')
    sub(scene, 'background', '0.22 0.25 0.28 1')
    sub(scene, 'shadows', 'true')
    sub(scene, 'grid', 'false')
    gui = sub(world, 'gui', fullscreen='false')
    view = sub(gui, 'plugin', filename='MinimalScene', name='3D View')
    props = sub(view, 'gz-gui')
    sub(props, 'property', 'false', type='bool', key='showTitleBar')
    sub(props, 'property', 'docked', type='string', key='state')
    sub(view, 'engine', 'ogre2')
    sub(view, 'scene', 'scene')
    sub(view, 'ambient_light', '0.65 0.65 0.65')
    sub(view, 'background_color', '0.22 0.25 0.28')
    sub(view, 'camera_pose', '0 -27 41 0 0.988 1.5708')
    for filename in ['GzSceneManager', 'InteractiveViewControl', 'CameraTracking', 'EntityContextMenuPlugin', 'SelectEntities']:
        plugin = sub(gui, 'plugin', filename=filename, name=filename)
        props = sub(plugin, 'gz-gui')
        sub(props, 'property', 'floating', type='string', key='state')
        sub(props, 'property', 'false', type='bool', key='showTitleBar')
        sub(props, 'property', '5', type='double', key='width')
        sub(props, 'property', '5', type='double', key='height')
    sun = sub(world, 'light', name='sun', type='directional')
    sub(sun, 'pose', '0 0 15 0 0 0')
    sub(sun, 'diffuse', '0.85 0.81 0.71 1')
    sub(sun, 'specular', '0.2 0.2 0.2 1')
    sub(sun, 'direction', '-0.3 0.2 -1')
    sub(sun, 'cast_shadows', 'true')

    def model(name):
        node = sub(world, 'model', name=name)
        sub(node, 'static', 'true')
        return sub(node, 'link', name='body')

    def shape(link, name, xyz, size, color, kind='box', solid=True, yaw=0, alpha=0):
        def geometry(node):
            geo = sub(node, 'geometry')
            part = sub(geo, kind)
            if kind == 'box':
                sub(part, 'size', ' '.join(f'{v:.5f}' for v in size))
            elif kind == 'cylinder':
                sub(part, 'radius', size[0]); sub(part, 'length', size[1])
            elif kind == 'sphere':
                sub(part, 'radius', size[0])
        pose = ' '.join(f'{v:.5f}' for v in (*xyz, 0, 0, yaw))
        if solid:
            col = sub(link, 'collision', name=name + '_collision')
            sub(col, 'pose', pose); geometry(col)
        vis = sub(link, 'visual', name=name)
        sub(vis, 'pose', pose); geometry(vis)
        mat = sub(vis, 'material')
        sub(mat, 'ambient', color); sub(mat, 'diffuse', color)
        sub(mat, 'specular', '0.18 0.18 0.18 1')
        if alpha:
            sub(vis, 'transparency', alpha)

    slab = model('floor_slab')
    shape(slab, 'slab', (0, 0, -0.125), (W, H, 0.25), CREAM)
    for x in [-12.5, 9.4]:
        shape(slab, 'apron_' + str(x), (x, -11.8, -0.125), (2.8, 1.6, 0.25), CREAM)
    floor = sub(model('floor_artwork'), 'visual', name='floor')
    sub(floor, 'pose', '0 0 0.008 0 0 0')
    sub(sub(sub(floor, 'geometry'), 'mesh'), 'uri', 'model://heritage_hall/meshes/floor.dae')
    mat = sub(floor, 'material')
    sub(mat, 'diffuse', '1 1 1 1'); sub(mat, 'ambient', '1 1 1 1')
    pbr = sub(sub(mat, 'pbr'), 'metal')
    sub(pbr, 'albedo_map', 'model://heritage_hall/materials/textures/floor.png')
    sub(pbr, 'roughness', '0.9'); sub(pbr, 'metalness', '0')

    walls = model('perimeter_walls')
    for name, xyz, size in [
        ('west', (-17.7, 0, 2.1), (.24, 22.24, 4.2)),
        ('east', (17.7, 0, 2.1), (.24, 22.24, 4.2)),
        ('north', (0, 11, 2.1), (35.4, .24, 4.2)),
        ('south_west', (-15.7, -11, 2.1), (4.0, .24, 4.2)),
        ('south_middle', (-1.55, -11, 2.1), (19.5, .24, 4.2)),
        ('south_east', (14.15, -11, 2.1), (7.1, .24, 4.2)),
    ]:
        shape(walls, name, xyz, size, DARK)
    # The two front doors are 2.4 m wide, genuinely open in collision geometry.
    for x, name in [(-12.5, 'entrance'), (9.4, 'exit')]:
        shape(walls, name + '_lintel', (x, -11, 3.8), (2.4, .24, .8), WOOD)
    # Interior timber pilasters and a display-height dado leave the top open.
    trim = model('wall_timber_panels')
    for i in range(23):
        x = -16.7 + i * 1.5
        shape(trim, f'back_panel_{i}', (x, 10.82, 1.7), (1.43, .08, 2.8), WOOD, solid=False)
        shape(trim, f'back_reveal_{i}', (x+.7, 10.72, 1.7), (.04, .1, 2.9), GOLD, solid=False)
    for i in range(14):
        y = -9.8 + i * 1.5
        for side in [-1, 1]:
            shape(trim, f'side_{side}_{i}', (side*17.52, y, 1.7), (.08, 1.43, 2.8), WOOD, solid=False)

    def segment(link, name, a, b, height=4.2, thickness=.16, color=WOOD):
        x1, y1 = xy(*a); x2, y2 = xy(*b)
        shape(link, name, ((x1+x2)/2, (y1+y2)/2, height/2),
              (math.hypot(x2-x1, y2-y1), thickness, height), color, yaw=math.atan2(y2-y1, x2-x1))

    rooms = model('service_rooms')
    # Back-left equipment room; bottom-right restroom and equipment room.
    for name, a, b in [
        ('back_room_east', (302, 28), (302, 112)),
        ('back_room_front_a', (226, 112), (248, 112)),
        ('back_room_front_b', (272, 112), (302, 112)),
        ('restroom_top_a', (884, 443), (900, 443)),
        ('restroom_top_b', (924, 443), (972, 443)),
        ('equipment_top', (996, 443), (1025, 443)),
        ('restroom_west', (884, 443), (884, 532)),
        ('service_divider', (956, 443), (956, 532)),
    ]:
        segment(rooms, name, a, b)
    # Solid exhibition partition with openings at both ends, matching the drawing.
    partition = model('history_partition')
    segment(partition, 'display_wall', (717, 211), (717, 397), 2.5, .22)
    segment(partition, 'right_wall', (934, 252), (934, 435), 2.5, .18)

    def cabinet(name, px, py, sx, sy, glass=True, count=3):
        x, y = xy(px, py)
        link = model(name)
        shape(link, 'plinth', (x, y, .4), (sx, sy, .8), WOOD)
        shape(link, 'rim', (x, y, .85), (sx+.04, sy+.04, .1), GOLD, solid=False)
        shape(link, 'lining', (x, y, .93), (sx-.12, sy-.12, .06), CREAM, solid=False)
        if glass:
            shape(link, 'case', (x, y, 1.4), (sx, sy, 1.0), GLASS, solid=True, alpha=.84)
            for dx in [-sx/2, sx/2]:
                for dy in [-sy/2, sy/2]:
                    shape(link, f'post_{dx}_{dy}', (x+dx, y+dy, 1.4), (.035, .035, 1.05), GOLD, solid=False)
        for i in range(count):
            dx = ((i+.5)/count-.5)*(sx-.18) if sx > sy else 0
            dy = ((i+.5)/count-.5)*(sy-.18) if sy >= sx else 0
            shape(link, f'foot_{i}', (x+dx, y+dy, 1.02), (.17, .12), GOLD, 'cylinder', False)
            shape(link, f'vase_{i}', (x+dx, y+dy, 1.23), (.17,), CREAM if i%2 else GOLD, 'sphere', False)
            shape(link, f'neck_{i}', (x+dx, y+dy, 1.4), (.07, .18), GOLD, 'cylinder', False)
        return link

    cabinet('west_tall_case', 423, 275, 1.6, 6.0, count=5)
    cabinet('east_tall_case', 676, 280, 1.6, 6.6, count=5)
    cabinet('south_small_case', 431, 392, 1.7, 2.6, count=1)
    cabinet('south_central_case', 553, 397, 5.8, 2.2, count=3)
    cabinet('masterpiece_long_case', 580, 493, 15.8, 2.0, count=11)
    cabinet('back_long_case', 529, 54, 14.4, 1.1, count=14)
    cabinet('back_small_case', 647, 136, 2.25, 2.0, count=2)
    cabinet('east_wall_case', 994, 167, 1.25, 4.5, count=5)
    cabinet('souvenir_counter', 994, 345, 1.4, 7.2, count=7)
    cabinet('history_counter', 862, 406, 5.2, 1.25, count=5)
    for px, name in [(415, 'craft_table_a'), (530, 'craft_table_b')]:
        cabinet(name, px, 139, 3.5, 1.6, glass=False, count=4)
        x, y = xy(px, 139)
        chairs = model(name + '_stools')
        for row in [-1, 1]:
            for i in [-1, 0, 1]:
                shape(chairs, f'stool_{row}_{i}', (x+i*1.0, y+row*1.25, .32), (.23, .64), WOOD, 'cylinder')

    column = model('central_column')
    cx, cy = xy(550, 282)
    shape(column, 'base', (cx, cy, .12), (2.32, .24), GOLD, 'cylinder')
    shape(column, 'drum', (cx, cy, .7), (2.1, 1.0), WOOD, 'cylinder')
    shape(column, 'crown', (cx, cy, 1.23), (2.16, .10), GOLD, 'cylinder', False)
    shape(column, 'central_pillar', (cx, cy, 1.9), (.72, 2.1), GOLD, 'cylinder')
    for i in range(48):
        a = i * math.tau / 48
        shape(column, f'fin_{i}', (cx+2.06*math.cos(a), cy+2.06*math.sin(a), .76), (.06, .13, .94), GOLD, solid=False, yaw=a)

    def screen(name, px, py, sx, sy, z=1.1):
        x, y = xy(px, py)
        link = model(name)
        shape(link, 'stand', (x, y, z/2), (sx, sy, z), WOOD)
        shape(link, 'bezel', (x, y, z+.06), (sx+.1, sy+.1, .12), DARK, solid=False)
        shape(link, 'display', (x, y, z+.13), (sx-.12, sy-.12, .02), '0.08 0.35 0.52 1', solid=False)
        for i in range(4):
            shape(link, f'ui_{i}', (x-sx*.31+i*sx*.2, y, z+.15), (sx*.14, sy*.65, .01), '0.3 0.62 0.74 1', solid=False)
    screen('overview_kiosk', 320, 335, 1.15, 2.15, 1.0)
    screen('interactive_table', 865, 99, 4.8, 3.0, .9)
    screen('history_media', 838, 322, 3.8, 1.7, 1.0)
    # A non-colliding start marker, rather than an extra robot obstructing the aisle.
    start = model('guide_start_marker')
    x, y = xy(326, 457)
    shape(start, 'disc', (x, y, .015), (.55, .015), '0.28 0.52 0.62 1', 'cylinder', False)
    (ROOT / 'worlds').mkdir(exist_ok=True)
    E.indent(sdf)
    E.ElementTree(sdf).write(ROOT / 'worlds/heritage_hall.sdf', encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':
    artwork()
    build()
    print('Built heritage_hall.sdf (35.4 x 22 m, height 4.2 m)')
